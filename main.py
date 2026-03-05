"""
main.py — LINE Insurance Claims Bot v2.0
FastAPI + LINE SDK v3 + Google Gemini AI

12-Factor compliance:
  III  – All config via env vars (see constants.py + .env.example)
  VI   – Stateless process: in-memory sessions + /data volume
  VII  – Port binding: Uvicorn :8000
  IX   – Disposability: lifespan context, fast startup
  XI   – Logs as event streams: logging → stdout + rotating file
"""

import logging
import os
import re

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    FlexMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)

# 1. Config & AI Models
from config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    GEMINI_API_KEY,
    configuration,
    gemini_model,
    genai,
    handler
)

# 2. Session & State Management
from session_manager import (
    user_sessions,
    get_session,
    set_state,
    reset_session,
    process_search_result
)

# 3. Mock Data
from mock_data import (
    search_policies_by_cid,
    search_policies_by_name,
    search_policies_by_plate,
    search_policies_by_phone
)

# 4. Flex Messages
from flex_messages import (
    create_request_info_flex,
    create_additional_info_prompt_flex,
    create_policy_info_flex,
    create_claim_submission_instructions_flex
)

# 5. Claim Engine (AI Logic)
from claim_engine import (
    extract_info_from_image_with_gemini,
    start_claim_analysis,
    extract_phone_from_response,
)

# 6. v2 Handlers (Document Verify & Claim Submission)
from handlers.documents import (
    handle_counterpart_answer,
    handle_ownership_answer,
    handle_document_image,
)
from handlers.submit import handle_submit_request

# 7. Storage (Claim & Sequence)
from storage.sequence import next_claim_id
from storage.claim_store import create_claim

# Module-level logger — all handlers must use logger.* not print()
logger = logging.getLogger(__name__)

# สร้าง FastAPI App
app = FastAPI(title="LINE Insurance Claim Bot")

# ==================== LINE Bot Handlers ====================

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """จัดการข้อความตัวอักษร"""
    user_id = event.source.user_id
    text = event.message.text.strip()
    logger.info("received_text user_id=%s chars=%d", user_id, len(text))

    session = get_session(user_id)
    current_state = session.get("state")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        try:
            # Case 1: เริ่มต้น Flow
            if text == "เช็คสิทธิ์เคลมด่วน":
                reset_session(user_id, initial_state="waiting_for_info")
                flex_message = create_request_info_flex()
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[FlexMessage(alt_text="กรุณาส่งข้อมูลเพื่อตรวจสอบสิทธิ์", contents=flex_message)]
                    )
                )
                return

            # Case 2: ค้นหากรมธรรม์
            if current_state == "waiting_for_info":
                text_clean = text.replace('-', '').replace(' ', '')
                if re.match(r'^\d{13}$', text_clean):
                    policies = search_policies_by_cid(text_clean)
                elif re.match(r'^\d{9,10}$', text_clean):
                    policies = search_policies_by_phone(text_clean)
                else:
                    policy = search_policies_by_plate(text)
                    policies = [policy] if policy else search_policies_by_name(text)

                process_search_result(line_bot_api, event, user_id, policies)
                return

            # Case 2.1: เลือกรถ (กรณีเจอนามสกุล/CID เดียวกันหลายคัน)
            if current_state == "waiting_for_vehicle_selection":
                if text.startswith("เลือกรถ:"):
                    plate = text.replace("เลือกรถ:", "")
                    search_results = session.get("search_results", [])
                    policy_info = next((p for p in search_results if p["plate"] == plate), None)
                    if policy_info:
                        process_search_result(line_bot_api, event, user_id, [policy_info])
                return

            # Case 3: ถามเรื่องคู่กรณี
            if current_state == "waiting_for_counterpart":
                if text in ["มีคู่กรณี", "ไม่มีคู่กรณี"]:
                    set_state(user_id, "waiting_for_image", has_counterpart=text, policy_info=session.get("policy_info"))
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                TextMessage(text=f"รับทราบค่ะ ({text})\n\n📸 ขั้นตอนต่อไป: กรุณาส่งรูปภาพความเสียหายของรถค่ะ"),
                                TextMessage(text="เพื่อให้ AI เริ่มต้นการประเมินเบื้องต้น")
                            ]
                        )
                    )
                return

            # Case 4: รับข้อมูลเพิ่มเติม (หลังส่งรูป)
            if current_state == "waiting_for_additional_info":
                additional_info = text if text != "ข้าม" else None
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="📝 บันทึกข้อมูลเรียบร้อยค่ะ กำลังส่งให้ AI วิเคราะห์สิทธิ์ให้ทันที...")]
                    )
                )

                start_claim_analysis(
                    line_bot_api, gemini_model, genai, user_id,
                    session.get("temp_image_bytes"), session.get("policy_info"),
                    additional_info, session.get("has_counterpart"), user_sessions
                )
                return

            # Case 5: จบการวิเคราะห์ (เลือกว่าจะส่งเคลม หรือ จบ)
            if current_state == "completed":
                if text == "ส่งเคลม":
                    # ── Bridge v1 → v2: สร้าง Claim ID แล้วเข้า flow ส่งเอกสาร ──
                    from flex_messages import (
                        create_claim_confirmed_flex,
                        create_document_checklist_flex,
                    )

                    claim_type = "CD"
                    claim_id = next_claim_id(claim_type)
                    has_counterpart = session.get("has_counterpart")
                    policy_info = session.get("policy_info")

                    create_claim(
                        claim_id, claim_type, user_id,
                        has_counterpart=has_counterpart,
                    )

                    # Set up v2 session structure
                    user_sessions[user_id] = {
                        "state": "uploading_documents",
                        "claim_id": claim_id,
                        "claim_type": claim_type,
                        "policy_info": policy_info,
                        "has_counterpart": has_counterpart,
                        "search_results": [],
                        "uploaded_docs": {},
                        "awaiting_ownership_for": None,
                        "additional_info": None,
                    }

                    confirm_flex = create_claim_confirmed_flex(claim_id, claim_type)
                    checklist_flex = create_document_checklist_flex(
                        claim_type, has_counterpart, {},
                    )

                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[
                                FlexMessage(
                                    alt_text=f"Claim ID: {claim_id}",
                                    contents=confirm_flex,
                                ),
                                TextMessage(
                                    text="🚀 เริ่มขั้นตอนรวบรวมเอกสารค่ะ กรุณาส่งรูปเอกสารทีละรายการตามรายการด้านล่าง",
                                ),
                                FlexMessage(
                                    alt_text="รายการเอกสารที่ต้องการ / Required documents",
                                    contents=checklist_flex,
                                ),
                            ],
                        )
                    )
                    logger.info("Bridged v1→v2 claim=%s user_id=%s", claim_id, user_id)
                    return

                elif text == "วิเคราะห์คันถัดไป":
                    reset_session(user_id, initial_state="waiting_for_info")
                    flex_message = create_request_info_flex()
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[FlexMessage(alt_text="กรุณาส่งข้อมูลเพื่อตรวจสอบสิทธิ์", contents=flex_message)]
                        )
                    )
                    return

                elif text == "จบการสนทนา":
                    reset_session(user_id)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text="🙏 ขอบคุณที่ใช้บริการเช็คสิทธิ์เคลมด่วนค่ะ หากต้องการความช่วยเหลือเพิ่มเติม สามารถพิมพ์หาเราได้ตลอดเวลานะคะ\n\nโชคดีและเดินทางปลอดภัยค่ะ! 🚗✨")]
                        )
                    )
                    return

            # ── v2 States: Document Upload Flow ──────────────────────────

            # Case 6: ตอบคำถามคู่กรณี (v2)
            if current_state == "waiting_for_counterpart" and session.get("claim_id"):
                handle_counterpart_answer(line_bot_api, event, user_id, user_sessions, text)
                return

            # Case 7: ยืนยันเจ้าของใบขับขี่ (v2)
            if current_state == "awaiting_ownership":
                handle_ownership_answer(line_bot_api, event, user_id, user_sessions, text)
                return

            # Case 8: อัปโหลดเอกสาร — text ที่ไม่ใช่คำสั่งพิเศษ จะถูก ignore
            if current_state == "uploading_documents":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(
                            text="📸 กรุณาส่งรูปเอกสารค่ะ (ใบขับขี่, เล่มทะเบียน, รูปความเสียหาย ฯลฯ)\n\nหากต้องการยกเลิก พิมพ์ 'ยกเลิก'"
                        )],
                    )
                )
                return

            # Case 9: พร้อมส่งเคลม (v2)
            if current_state == "ready_to_submit":
                if text in ("ยืนยันส่งเคลม", "ส่งเคลม", "ยืนยัน", "confirm"):
                    handle_submit_request(line_bot_api, event, user_id, user_sessions)
                    return
                else:
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(
                                text="� เอกสารครบแล้วค่ะ! กด 'ยืนยันส่งเคลม' เพื่อส่งคำร้อง\n\nหรือส่งรูปเอกสารเพิ่มเติมได้"
                            )],
                        )
                    )
                    return

            # Case 10: ส่งเคลมเสร็จแล้ว (v2)
            if current_state == "submitted":
                reset_session(user_id)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(
                            text="✅ คำร้องของคุณถูกส่งเรียบร้อยแล้วค่ะ\n\nหากต้องการเริ่มเคลมใหม่ พิมพ์ 'เช็คสิทธิ์เคลมด่วน'"
                        )],
                    )
                )
                return

            # Fallback for general menu
            if current_state == "completed" or current_state == "idle" or current_state is None:
                from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction
                quick_reply = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))
                ])
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(
                            text='👋 สวัสดีค่ะ!\n\nต้องการตรวจสอบสิทธิ์การเคลมประกันรถยนต์ด้วย AI หรือแจ้งเหตุฉุกเฉิน กดปุ่มด้านล่างได้เลยค่ะ',
                            quick_reply=quick_reply
                        )]
                    )
                )

        except Exception as e:
            logger.exception("Error in handle_text_message user_id=%s", user_id)


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    """จัดการรูปภาพ"""
    user_id = event.source.user_id
    session = get_session(user_id)
    current_state = session.get("state")
    logger.info("received_image user_id=%s state=%s", user_id, current_state)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        try:
            # ดาวน์โหลดรูป
            message_id = event.message.id
            image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
            headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
            with httpx.Client() as client:
                response = client.get(image_url, headers=headers)
                response.raise_for_status()
                image_bytes = response.content

            # Case 1: OCR เพื่อหาข้อมูลกรมธรรม์
            if current_state == "waiting_for_info":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="⏳ กำลังค้นหาข้อมูลจากรูปภาพ...")]
                    )
                )
                info = extract_info_from_image_with_gemini(gemini_model, image_bytes)
                policies = []
                if info["type"] == "id_card" and info["value"]:
                    policies = search_policies_by_cid(info["value"])
                elif info["type"] == "license_plate" and info["value"]:
                    policy = search_policies_by_plate(info["value"])
                    policies = [policy] if policy else []

                process_search_result(line_bot_api, event, user_id, policies, use_push=True)

            # Case 2: รูปความเสียหาย
            elif current_state == "waiting_for_image":
                set_state(user_id, "waiting_for_additional_info",
                          temp_image_bytes=image_bytes,
                          policy_info=session.get("policy_info"),
                          has_counterpart=session.get("has_counterpart"))

                flex_prompt = create_additional_info_prompt_flex()
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(text="✅ ได้รับรูปภาพความเสียหายแล้วค่ะ"),
                            FlexMessage(alt_text="ขอข้อมูลเพิ่มเติม", contents=flex_prompt)
                        ]
                    )
                )

            # Case 3: อัปโหลดเอกสาร (v2 flow — AI categorise + extract)
            elif current_state in ("uploading_documents", "ready_to_submit"):
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="⏳ กำลังตรวจสอบเอกสาร...")],
                    )
                )
                handle_document_image(
                    line_bot_api, user_id, user_sessions,
                    image_bytes, content_type="image/jpeg",
                )

            else:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="📸 ได้รับรูปภาพแล้วค่ะ แต่ตอนนี้ยังไม่ถึงขั้นตอนส่งรูปนะคะ\n\nพิมพ์ 'เช็คสิทธิ์เคลมด่วน' เพื่อเริ่มใหม่ค่ะ")]
                    )
                )

        except Exception as e:
            logger.exception("Error in handle_image_message user_id=%s", user_id)


# ==================== FastAPI Endpoints ====================

@app.get("/")
async def root():
    return JSONResponse({"status": "running", "message": "LINE Insurance Claim Bot", "version": "2.0.0"})


async def _handle_webhook(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        # Malformed JSON, missing 'events' key, or non-UTF-8 encoding — all are
        # client errors. Return 400 rather than letting them bubble to 500.
        logger.warning("malformed_webhook body_len=%d error=%s", len(body), exc)
        raise HTTPException(status_code=400, detail="Malformed request body")
    return JSONResponse(content={"status": "ok"})



@app.post("/callback")
async def callback(request: Request):
    return await _handle_webhook(request)


@app.post("/webhook")
async def webhook(request: Request):
    return await _handle_webhook(request)


@app.get("/health")
async def health_check():
    line_ok = bool(LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET)
    gemini_ok = bool(GEMINI_API_KEY)
    checks = {"line_api": line_ok, "gemini_api": gemini_ok}
    status = "healthy" if (line_ok and gemini_ok) else "degraded"
    return JSONResponse({
        "status": status,
        "line_configured": line_ok,
        "gemini_configured": gemini_ok,
        "checks": checks,
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info("Bot starting on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
