"""
main.py — LINE Insurance Claims Bot v2.0
FastAPI + LINE SDK v3 + Azure OpenAI

12-Factor compliance:
  III  – All config via env vars (see constants.py + .env.example)
  VI   – Stateless process: in-memory sessions + /data volume
  VII  – Port binding: Uvicorn :8000
  IX   – Disposability: lifespan context, fast startup
  XI   – Logs as event streams: logging → stdout + rotating file
"""

import logging
import os

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
    FlexMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
)

# 1. Config & AI Models
from config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    configuration,
    handler,
)

# 2. Session & State Management
from session_manager import (
    user_sessions,
    get_session,
    reset_session,
)

# 3. v2 Handlers — all state transitions delegated here
from handlers.trigger import (
    is_trigger,
    handle_trigger,
    handle_claim_type_selection,
)
from handlers.identity import (
    handle_policy_text,
    handle_policy_image,
    handle_vehicle_selection,
)
from handlers.documents import (
    handle_document_image,
    handle_damage_photo_image,
    handle_confirm_claim,
    handle_identity_doc_image,
    handle_counterpart_answer,
    handle_ownership_answer,
)
from handlers.submit import handle_submit_request

# 4. Constants
from constants import CANCEL_KEYWORDS

from local_chat import router as local_chat_router

# 6. Dashboards Router
from dashboards_router import router as dashboards_router

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
app.include_router(local_chat_router)
app.include_router(dashboards_router)

# ==================== LINE Bot Handlers ====================


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """จัดการข้อความตัวอักษร — delegates to v2 handler modules."""
    user_id = event.source.user_id
    text = event.message.text.strip()
    logger.info("received_text user_id=%s chars=%d", user_id, len(text))

    session = get_session(user_id)
    current_state = session.get("state")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        try:
            # ── Cancel keywords (any active state) ──────────────────────
            if current_state not in (None, "idle") and text.lower() in CANCEL_KEYWORDS:
                reset_session(user_id)
                welcome_qr = QuickReply(
                    items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="👋 สวัสดีค่ะ!\n\nต้องการตรวจสอบสิทธิ์การเคลมประกัน กดปุ่มด้านล่างได้เลยค่ะ",
                                quick_reply=welcome_qr,
                            )
                        ],
                    )
                )
                return

            # ── Trigger detection (idle / no state) ─────────────────────
            if current_state in (None, "idle"):
                if is_trigger(text):
                    handle_trigger(line_bot_api, event, user_id, user_sessions, text)
                    return
                # Not a trigger — show menu
                quick_reply = QuickReply(
                    items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="👋 สวัสดีค่ะ!\n\nต้องการตรวจสอบสิทธิ์การเคลมประกัน กดปุ่มด้านล่างได้เลยค่ะ",
                                quick_reply=quick_reply,
                            )
                        ],
                    )
                )
                return

            # ── Claim type selection (ambiguous trigger) ────────────────
            if current_state == "detecting_claim_type":
                handle_claim_type_selection(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Policy verification by text ─────────────────────────────
            if current_state == "verifying_policy":
                handle_policy_text(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Vehicle selection ────────────────────────────────────────
            if current_state == "waiting_for_vehicle_selection":
                handle_vehicle_selection(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Counterpart question (CD only) ──────────────────────────
            if current_state == "waiting_for_counterpart":
                handle_counterpart_answer(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Phase 1: Damage photos — text reminder (CD) ─────────────
            if current_state == "uploading_damage_photos":
                if text == "เริ่มทำการวิเคราะห์":
                    from handlers.documents import handle_start_damage_analysis
                    handle_start_damage_analysis(line_bot_api, event, user_id, user_sessions)
                    return

                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="📸 กรุณาส่งรูปถ่ายความเสียหายของรถค่ะ / Please send car damage photos.\n\nพิมพ์ 'เริ่มทำการวิเคราะห์' ถ้ารูปครบแล้ว",
                            )
                        ],
                    )
                )
                return

            # ── Phase 2: Confirm claim (CD) ─────────────────────────────
            if current_state == "confirming_claim":
                handle_confirm_claim(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Phase 3: Identity docs — text reminder (CD) ─────────────
            if current_state == "uploading_identity_docs":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="📄 กรุณาส่งรูปใบขับขี่หรือสมุดเล่มทะเบียนรถค่ะ / Please send driving license or vehicle registration photo.\n\nพิมพ์ 'ยกเลิก' เพื่อเริ่มใหม่ / Type 'ยกเลิก' to cancel.",
                            )
                        ],
                    )
                )
                return

            # ── Ownership answer (driving license counterpart) ──────────
            if current_state == "awaiting_ownership":
                handle_ownership_answer(line_bot_api, event, user_id, user_sessions, text)
                return

            # ── Document upload state — text reminders (H claims) ───────
            if current_state == "uploading_documents":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="📸 กรุณาส่งรูปถ่ายเอกสารค่ะ / Please send a document photo.\n\nพิมพ์ 'ยกเลิก' เพื่อเริ่มใหม่ / Type 'ยกเลิก' to cancel.",
                            )
                        ],
                    )
                )
                return

            # ── Submit claim ────────────────────────────────────────────
            if current_state == "ready_to_submit":
                if text in ("ส่งคำร้อง", "ส่งเคลม"):
                    handle_submit_request(line_bot_api, event, user_id, user_sessions)
                    return
                # any other text — remind them with a clickable button
                submit_qr = QuickReply(
                    items=[QuickReplyItem(action=MessageAction(label="📤 ส่งคำร้อง", text="ส่งคำร้อง"))]
                )
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="📋 เอกสารครบแล้วค่ะ กด 'ส่งคำร้อง' เพื่อส่ง / Documents complete. Tap 'ส่งคำร้อง' to submit.",
                                quick_reply=submit_qr,
                            )
                        ],
                    )
                )
                return

            # ── Submitted — session done ────────────────────────────────
            if current_state == "submitted":
                reset_session(user_id)
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[
                            TextMessage(
                                text="🙏 ขอบคุณที่ใช้บริการค่ะ! / Thank you!\n\nพิมพ์ข้อความใหม่เพื่อเริ่มต้นเคลมใหม่ได้เลยค่ะ",
                            )
                        ],
                    )
                )
                return

            # ── Fallback — show menu ────────────────────────────────────
            quick_reply = QuickReply(
                items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
            )
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="👋 สวัสดีค่ะ!\n\nต้องการตรวจสอบสิทธิ์การเคลมประกัน กดปุ่มด้านล่างได้เลยค่ะ",
                            quick_reply=quick_reply,
                        )
                    ],
                )
            )

        except Exception as e:
            logger.exception("Error in handle_text_message user_id=%s", user_id)


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    """จัดการรูปภาพ — delegates to v2 handler modules."""
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

            # ── Policy verification by image (OCR) ─────────────────────
            if current_state == "verifying_policy":
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="⏳ กำลังอ่านข้อมูลจากรูปภาพ... / Reading image...")],
                    )
                )
                handle_policy_image(line_bot_api, user_id, user_sessions, image_bytes)
                return

            # ── Phase 1: Damage photo upload (CD) ──────────────────────
            if current_state == "uploading_damage_photos":
                handle_damage_photo_image(line_bot_api, event, user_id, user_sessions, image_bytes)
                return

            # ── Phase 2: Confirming claim — accept extra damage photos ──
            if current_state == "confirming_claim":
                # Allow sending more damage photos even during confirmation
                handle_damage_photo_image(line_bot_api, event, user_id, user_sessions, image_bytes)
                return

            # ── Phase 3: Identity doc upload (CD) ──────────────────────
            if current_state == "uploading_identity_docs":
                handle_identity_doc_image(line_bot_api, event, user_id, user_sessions, image_bytes)
                return

            # ── Document upload — Health claims (single phase) ─────────
            if current_state in ("uploading_documents", "waiting_for_claim_documents"):
                handle_document_image(line_bot_api, event, user_id, user_sessions, image_bytes)
                return

            # ── Unexpected image ────────────────────────────────────────
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[
                        TextMessage(
                            text="📸 ได้รับรูปภาพแล้วค่ะ แต่ตอนนี้ยังไม่ถึงขั้นตอนส่งรูปนะคะ\n\nพิมพ์ 'เช็คสิทธิ์เคลมด่วน' เพื่อเริ่มใหม่ค่ะ / Not expecting an image now. Type a claim keyword to start."
                        )
                    ],
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
    from constants import AZURE_OPENAI_API_KEY
    line_ok = bool(LINE_CHANNEL_ACCESS_TOKEN and LINE_CHANNEL_SECRET)
    ai_ok = bool(AZURE_OPENAI_API_KEY)
    checks = {"line_api": line_ok, "azure_openai": ai_ok}
    status = "healthy" if (line_ok and ai_ok) else "degraded"
    return JSONResponse({
        "status": status,
        "line_configured": line_ok,
        "ai_configured": ai_ok,
        "checks": checks,
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info("Bot starting on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
