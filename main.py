import re
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent
)
import httpx

# 1. Config & AI Models
from config import (
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    GEMINI_API_KEY,
    configuration,
    gemini_model,
    genai
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
    create_additional_info_prompt_flex
)

# 5. Claim Engine (AI Logic)
from claim_engine import (
    extract_info_from_image_with_gemini,
    start_claim_analysis
)

# สร้าง FastAPI App
app = FastAPI(title="LINE Insurance Claim Bot")
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ==================== LINE Bot Handlers ====================

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """จัดการข้อความตัวอักษร"""
    user_id = event.source.user_id
    text = event.message.text.strip()
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
                    policies = session.get("search_results", [])
                    policy_info = next((p for p in policies if p["plate"] == plate), None)
                    if policy_info:
                        process_search_result(line_bot_api, event, user_id, [policy_info])
                return

            # Case 3: ถามเรื่องคู่กรณี
            if current_state == "waiting_for_counterpart":
                if text in ["มีคู่กรณี", "ไม่มีคู่กรณี"]:
                    set_state(user_id, "waiting_for_image", has_counterpart=text)
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=event.reply_token,
                            messages=[TextMessage(text=f"รับทราบค่ะ ({text})\n\n📸 กรุณาส่ง **รูปภาพความเสียหาย** ของรถเพื่อเริ่มการวิเคราะห์ค่ะ")]
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

        except Exception as e:
            print(f"Error in handle_text_message: {str(e)}")

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    """จัดการรูปภาพ"""
    user_id = event.source.user_id
    session = get_session(user_id)
    current_state = session.get("state")

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        try:
            # ดาวน์โหลดรูป
            message_id = event.message.id
            image_url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
            headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
            with httpx.Client() as client:
                response = client.get(image_url, headers=headers)
                image_bytes = response.content

            # Case 1: OCR เพื่อหาข้อมูลกรมธรรม์
            if current_state == "waiting_for_info":
                info = extract_info_from_image_with_gemini(gemini_model, image_bytes)
                if info["type"] == "id_card" and info["value"]:
                    policies = search_policies_by_cid(info["value"])
                elif info["type"] == "license_plate" and info["value"]:
                    policy = search_policies_by_plate(info["value"])
                    policies = [policy] if policy else []
                else:
                    policies = []
                process_search_result(line_bot_api, event, user_id, policies, use_push=True)

            # Case 2: รูปความเสียหาย
            elif current_state == "waiting_for_image":
                set_state(user_id, "waiting_for_additional_info", temp_image_bytes=image_bytes)
                flex_prompt = create_additional_info_prompt_flex()
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[FlexMessage(alt_text="ขอข้อมูลเพิ่มเติม", contents=flex_prompt)]
                    )
                )

        except Exception as e:
            print(f"Error in handle_image_message: {str(e)}")

# ==================== FastAPI Endpoints ====================

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400)
    return JSONResponse(content={"status": "ok"})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Bot starting on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
