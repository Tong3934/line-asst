"""
local_chat.py — Local Chat Testing Interface

Bypasses LINE SDK so developers can test the full bot conversation
flow from a browser without a LINE channel or ngrok tunnel.

Endpoints
---------
GET  /local-chat            → HTML chat UI
POST /local-chat/message    → Send a text message, returns bot replies as JSON
POST /local-chat/image      → Send an image upload, returns bot replies as JSON
GET  /local-chat/session    → Inspect current session state (debug)
POST /local-chat/reset      → Reset the session
"""

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from linebot.v3.messaging import (
    FlexMessage,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    ReplyMessageRequest,
    TextMessage,
)

from constants import CANCEL_KEYWORDS
from handlers.trigger import handle_trigger, handle_claim_type_selection, is_trigger
from handlers.identity import handle_policy_text, handle_policy_image, handle_vehicle_selection
from handlers.documents import (
    handle_document_image,
    handle_damage_photo_image,
    handle_confirm_claim,
    handle_identity_doc_image,
    handle_counterpart_answer,
    handle_ownership_answer,
)
from handlers.submit import handle_submit_request
from session_manager import (
    get_session,
    reset_session,
    user_sessions,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/local-chat", tags=["local-chat"])

# ---------------------------------------------------------------------------
# Mock LINE API — captures outgoing messages instead of calling LINE servers
# ---------------------------------------------------------------------------

class _MockLineAPI:
    """Intercepts reply_message / push_message and stores them for return."""

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def _serialise(self, msg: Any) -> Dict[str, Any]:
        """Convert a LINE SDK message object to a plain JSON-serialisable dict."""
        if isinstance(msg, TextMessage):
            out: Dict[str, Any] = {"type": "text", "text": msg.text}
            if msg.quick_reply:
                out["quick_reply"] = {
                    "items": [
                        {
                            "label": item.action.label,
                            "text": item.action.text,
                        }
                        for item in msg.quick_reply.items
                    ]
                }
            return out

        if isinstance(msg, FlexMessage):
            contents = msg.contents
            # linebot.v3 FlexContainer → dict
            if hasattr(contents, "to_dict"):
                contents_dict = contents.to_dict()
            elif isinstance(contents, dict):
                contents_dict = contents
            else:
                try:
                    contents_dict = vars(contents)
                except Exception:
                    contents_dict = {}
            return {
                "type": "flex",
                "alt_text": msg.alt_text,
                "contents": contents_dict,
            }

        return {"type": "unknown", "text": str(msg)}

    # ------------------------------------------------------------------
    def reply_message(self, request: ReplyMessageRequest) -> None:
        for m in request.messages:
            self.messages.append(self._serialise(m))

    def push_message(self, request: PushMessageRequest) -> None:
        for m in request.messages:
            self.messages.append(self._serialise(m))


# ---------------------------------------------------------------------------
# Shared mock event — just needs .reply_token and .source.user_id
# ---------------------------------------------------------------------------

class _LocalEvent:
    class _Source:
        def __init__(self, uid: str) -> None:
            self.user_id = uid

    def __init__(self, user_id: str) -> None:
        self.reply_token = "local_token"
        self.source = self._Source(user_id)


# ---------------------------------------------------------------------------
# Core message dispatcher — mirrors main.py handle_text_message logic
# ---------------------------------------------------------------------------

def _dispatch_text(user_id: str, text: str, api: _MockLineAPI) -> None:
    """Process one text message and populate api.messages with bot replies.

    Delegates to v2 handler modules so the local-chat flow matches
    the designed journey (user-journey.md state machine).
    """
    event = _LocalEvent(user_id)
    session = get_session(user_id)
    current_state = session.get("state")

    # ── Cancel keywords (any active state) ──────────────────────────────────
    if current_state not in (None, "idle") and text.lower() in CANCEL_KEYWORDS:
        reset_session(user_id)
        quick_reply = QuickReply(
            items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
        )
        api.reply_message(
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

    # ── Trigger detection (idle / no state) ─────────────────────────────────
    if current_state in (None, "idle"):
        if is_trigger(text):
            handle_trigger(api, event, user_id, user_sessions, text)
            return
        # Not a trigger — show menu
        quick_reply = QuickReply(
            items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
        )
        api.reply_message(
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

    # ── Claim type selection (ambiguous trigger) ────────────────────────────
    if current_state == "detecting_claim_type":
        handle_claim_type_selection(api, event, user_id, user_sessions, text)
        return

    # ── Policy verification by text ─────────────────────────────────────────
    if current_state == "verifying_policy":
        handle_policy_text(api, event, user_id, user_sessions, text)
        return

    # ── Vehicle selection ────────────────────────────────────────────────────
    if current_state == "waiting_for_vehicle_selection":
        handle_vehicle_selection(api, event, user_id, user_sessions, text)
        return

    # ── Counterpart question (CD only) ──────────────────────────────────────
    if current_state == "waiting_for_counterpart":
        handle_counterpart_answer(api, event, user_id, user_sessions, text)
        return

    # ── Ownership answer (driving license in with-counterpart CD claim) ─────
    if current_state == "awaiting_ownership":
        handle_ownership_answer(api, event, user_id, user_sessions, text)
        return

    # ── Phase 1: Damage photos — text reminder (CD) ─────────────────────────
    if current_state == "uploading_damage_photos":
        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text="📸 กรุณาส่งรูปถ่ายความเสียหาย / Please send damage photos.\n\nพิมพ์ 'ยกเลิก' เพื่อเริ่มใหม่ / Type 'ยกเลิก' to cancel.",
                    )
                ],
            )
        )
        return

    # ── Phase 2: Claim confirmation (CD) ────────────────────────────────────
    if current_state == "confirming_claim":
        handle_confirm_claim(api, event, user_id, user_sessions, text)
        return

    # ── Phase 3: Identity docs — text reminder (CD) ─────────────────────────
    if current_state == "uploading_identity_docs":
        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(
                        text="📸 กรุณาส่งเอกสารยืนยันตัวตน / Please send identity documents.\n\nพิมพ์ 'ยกเลิก' เพื่อเริ่มใหม่ / Type 'ยกเลิก' to cancel.",
                    )
                ],
            )
        )
        return

    # ── Document upload state — text reminders (Health) ─────────────────────
    if current_state == "uploading_documents":
        api.reply_message(
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

    # ── Submit claim ────────────────────────────────────────────────────────
    if current_state == "ready_to_submit":
        if text == "ส่งคำร้อง":
            handle_submit_request(api, event, user_id, user_sessions)
            return
        # any other text — remind them with a clickable button
        submit_qr = QuickReply(
            items=[QuickReplyItem(action=MessageAction(label="📤 ส่งคำร้อง", text="ส่งคำร้อง"))]
        )
        api.reply_message(
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

    # ── Submitted — session done ────────────────────────────────────────────
    if current_state == "submitted":
        reset_session(user_id)
        api.reply_message(
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

    # ── Fallback — show menu ────────────────────────────────────────────────
    quick_reply = QuickReply(
        items=[QuickReplyItem(action=MessageAction(label="🚀 เช็คสิทธิ์เคลมด่วน", text="เช็คสิทธิ์เคลมด่วน"))]
    )
    api.reply_message(
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


def _dispatch_image(user_id: str, image_bytes: bytes, api: _MockLineAPI) -> None:
    """Process one image upload and populate api.messages with bot replies.

    Delegates to v2 handler modules for policy verification (OCR)
    and document upload (categorise → extract → checklist).
    """
    event = _LocalEvent(user_id)
    session = get_session(user_id)
    current_state = session.get("state")

    # ── Policy verification by image (OCR) ──────────────────────────────────
    if current_state == "verifying_policy":
        api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="⏳ กำลังอ่านข้อมูลจากรูปภาพ... / Reading image...")],
            )
        )
        handle_policy_image(api, user_id, user_sessions, image_bytes)
        return

    # ── Phase 1: Damage photo upload (CD) ───────────────────────────────────
    if current_state == "uploading_damage_photos":
        handle_damage_photo_image(api, user_id, user_sessions, image_bytes)
        return

    # ── Phase 2: Confirming claim — accept extra damage photos ──────────────
    if current_state == "confirming_claim":
        handle_damage_photo_image(api, user_id, user_sessions, image_bytes)
        return

    # ── Phase 3: Identity doc upload (CD) ───────────────────────────────────
    if current_state == "uploading_identity_docs":
        handle_identity_doc_image(api, event, user_id, user_sessions, image_bytes)
        return

    # ── Document upload — Health claims (single phase) ──────────────────────
    if current_state in ("uploading_documents", "waiting_for_claim_documents"):
        handle_document_image(api, event, user_id, user_sessions, image_bytes)
        return

    # ── Unexpected image ────────────────────────────────────────────────────
    api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(
                    text="📸 ได้รับรูปภาพแล้วค่ะ แต่ตอนนี้ยังไม่ถึงขั้นตอนส่งรูปนะคะ\n\nพิมพ์ 'เช็คสิทธิ์เคลมด่วน' เพื่อเริ่มใหม่ค่ะ / Not expecting an image now. Type a claim keyword to start."
                )
            ],
        )
    )


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse, include_in_schema=False)
@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def local_chat_ui():
    """Serve the chat UI HTML page."""
    import os
    html_path = os.path.join(os.path.dirname(__file__), "dashboards", "local_chat.html")
    with open(html_path, encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.post("/message")
async def send_message(
    user_id: str = Form(default="local_test_user"),
    text: str = Form(...),
):
    """Process a text message and return bot replies."""
    api = _MockLineAPI()
    try:
        # start_claim_analysis is blocking (Gemini call) — run in thread pool
        await asyncio.get_event_loop().run_in_executor(None, _dispatch_text, user_id, text, api)
    except Exception as exc:
        logger.exception("local_chat send_message error user_id=%s", user_id)
        return JSONResponse({"messages": [{"type": "text", "text": f"❌ ข้อผิดพลาด: {exc}"}]})
    return JSONResponse({"messages": api.messages})


@router.post("/image")
async def send_image(
    user_id: str = Form(default="local_test_user"),
    file: UploadFile = File(...),
):
    """Process an image upload and return bot replies."""
    image_bytes = await file.read()
    api = _MockLineAPI()
    try:
        await asyncio.get_event_loop().run_in_executor(None, _dispatch_image, user_id, image_bytes, api)
    except Exception as exc:
        logger.exception("local_chat send_image error user_id=%s", user_id)
        return JSONResponse({"messages": [{"type": "text", "text": f"❌ ข้อผิดพลาด: {exc}"}]})
    return JSONResponse({"messages": api.messages})


@router.get("/session")
async def get_session_state(user_id: str = "local_test_user"):
    """Return the current session state for debugging."""
    session = get_session(user_id)
    safe = {k: v for k, v in session.items() if k != "temp_image_bytes"}
    return JSONResponse({"user_id": user_id, "session": safe})


@router.post("/reset")
async def reset(user_id: str = Form(default="local_test_user")):
    """Reset the session."""
    reset_session(user_id)
    return JSONResponse({"status": "reset", "user_id": user_id})
