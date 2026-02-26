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

import io
import json
import logging
import logging.handlers
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    MessagingApi,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import ImageMessageContent, MessageEvent, TextMessageContent

# ── Bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()

from constants import (
    ALL_STATUSES,
    CANCEL_KEYWORDS,
    DATA_DIR,
    LINE_API_HOST,
    LINE_DATA_API_HOST,
    VALID_TRANSITIONS,
    APP_VERSION,
)

# ── Structured Logging (12-Factor XI) ─────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

_log_format = "%(asctime)s %(levelname)s %(name)s %(message)s"
_handlers: list = [logging.StreamHandler()]
try:
    _file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setFormatter(logging.Formatter(_log_format))
    _handlers.append(_file_handler)
except OSError:
    pass

logging.basicConfig(level=LOG_LEVEL, format=_log_format, handlers=_handlers)
logger = logging.getLogger(__name__)
logger.info("LINE Insurance Claim Bot starting — version %s", APP_VERSION)

# ── Environment Validation ────────────────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN: str = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET: str       = os.environ["LINE_CHANNEL_SECRET"]
GEMINI_API_KEY: str            = os.environ["GEMINI_API_KEY"]

# ── Data Directory Init ───────────────────────────────────────────────────────
def _init_data_dir() -> None:
    for sub in ("claims", "logs", "token_records"):
        path = os.path.join(DATA_DIR, sub)
        os.makedirs(path, exist_ok=True)
        logger.debug("Data dir ready: %s", path)


_init_data_dir()

# ── LINE Setup ────────────────────────────────────────────────────────────────
configuration = Configuration(
    access_token=LINE_CHANNEL_ACCESS_TOKEN,
    host=LINE_API_HOST,
)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ── In-Memory Session Store (12-Factor VI) ────────────────────────────────────
user_sessions: Dict[str, Dict] = {}


def _new_session() -> Dict:
    return {
        "state": "idle",
        "claim_id": None,
        "claim_type": None,
        "policy_info": None,
        "has_counterpart": None,
        "search_results": [],
        "uploaded_docs": {},
        "awaiting_ownership_for": None,
        "additional_info": None,
    }


# ── Jinja2 Templates (dashboards) ─────────────────────────────────────────────
DASHBOARDS_DIR = os.path.join(os.path.dirname(__file__), "dashboards")
os.makedirs(DASHBOARDS_DIR, exist_ok=True)
templates = Jinja2Templates(directory=DASHBOARDS_DIR)

# ── FastAPI App ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup complete (12-Factor IX)")
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="LINE Insurance Claim Bot",
    version=APP_VERSION,
    lifespan=lifespan,
)


# ── Utility: phone number extraction (used by AI response parsing) ──────────
_PHONE_RE = re.compile(
    r'(?:โทร|เบอร์|โทรศัพท์|แจ้งเหตุ)\s*[:\-]?\s*(\d[\d\-]+)',
    re.UNICODE,
)


def extract_phone_from_response(text: str) -> Optional[str]:
    """Extract the first Thai-prefixed phone number from AI response text.

    Matches patterns like:\n      โทร 1557 → '1557'\n      เบอร์: 098-765-4321 → '0987654321'\n      โทรศัพท์: 02-123-4567 → '021234567'

    Returns the digit-only string, or None if no match.
    """
    m = _PHONE_RE.search(text or "")
    if m:
        return re.sub(r'\D', '', m.group(1))
    return None


@app.get("/")
async def root():
    return {
        "status": "running",
        "message": f"LINE Insurance Claim Bot v{APP_VERSION}",
        "version": APP_VERSION,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Health Endpoint
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/health")
async def health_check():
    line_configured  = bool(LINE_CHANNEL_ACCESS_TOKEN)
    gemini_configured = bool(GEMINI_API_KEY)
    data_ok          = os.path.isdir(os.path.join(DATA_DIR, "claims"))
    ok = line_configured and gemini_configured and data_ok
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "healthy" if ok else "degraded",
            "version": APP_VERSION,
            "line_configured":   line_configured,
            "gemini_configured": gemini_configured,
            "checks": {
                "line_token_set":   line_configured,
                "gemini_key_set":   gemini_configured,
                "data_dir_writable": data_ok,
            },
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# LINE Webhook  (/callback and legacy /webhook alias)
# ══════════════════════════════════════════════════════════════════════════════
async def _handle_webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body      = await request.body()
    body_text = body.decode("utf-8")
    logger.debug("Webhook received body_len=%d", len(body_text))
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    return JSONResponse({"status": "ok"})


@app.post("/callback")
async def callback(request: Request):
    return await _handle_webhook(request)


@app.post("/webhook")  # legacy alias kept for backward compat / test suites
async def webhook(request: Request):
    return await _handle_webhook(request)


# ── Text Message Handler ──────────────────────────────────────────────────────
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    from handlers.trigger   import is_trigger, handle_trigger, handle_claim_type_selection
    from handlers.identity  import handle_policy_text, handle_vehicle_selection
    from handlers.documents import handle_counterpart_answer, handle_ownership_answer
    from handlers.submit    import handle_submit_request

    user_id = event.source.user_id
    text    = event.message.text.strip()
    t0      = time.monotonic()

    if user_id not in user_sessions:
        user_sessions[user_id] = _new_session()

    session = user_sessions[user_id]
    state   = session.get("state", "idle")
    logger.info("text user=%s state=%s len=%d", user_id, state, len(text))

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        # 1. Cancel / reset
        if any(kw in text.lower() for kw in CANCEL_KEYWORDS):
            user_sessions[user_id] = _new_session()
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=(
                            "🔄 ยกเลิกการเคลมแล้ว / Claim cancelled.\n"
                            "พิมพ์ 'เคลม' เพื่อเริ่มใหม่ / Type 'claim' to start over."
                        )
                    )],
                )
            )
            return

        # 2. Claim type selection (after ambiguous trigger)
        if state == "detecting_claim_type":
            handle_claim_type_selection(line_bot_api, event, user_id, user_sessions, text)
            return

        # 3. New claim trigger
        if is_trigger(text):
            handle_trigger(line_bot_api, event, user_id, user_sessions, text)
            return

        # 4. Policy verification (typed CID / plate / name)
        if state in ("verifying_policy", "waiting_for_info"):
            handle_policy_text(line_bot_api, event, user_id, user_sessions, text)
            return

        # 5. Vehicle selection
        if state == "waiting_for_vehicle_selection":
            handle_vehicle_selection(line_bot_api, event, user_id, user_sessions, text)
            return

        # 6. Counterpart question (CD)
        if state == "waiting_for_counterpart":
            handle_counterpart_answer(line_bot_api, event, user_id, user_sessions, text)
            return

        # 7. Ownership question for driving license
        if state == "awaiting_ownership":
            handle_ownership_answer(line_bot_api, event, user_id, user_sessions, text)
            return

        # 8. Submit command
        if state in ("uploading_documents", "ready_to_submit") and (
            "ส่งคำร้อง" in text or "submit" in text.lower()
        ):
            handle_submit_request(line_bot_api, event, user_id, user_sessions)
            return

        # 9. Already submitted
        if state == "submitted":
            claim_id = session.get("claim_id", "")
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text=(
                            f"✅ คำร้อง {claim_id} ส่งแล้ว / Claim submitted.\n"
                            "พิมพ์ 'เคลม' เพื่อเริ่มคำร้องใหม่ / Type 'claim' to start a new one."
                        )
                    )],
                )
            )
            return

        # 10. Default: welcome / help
        from flex_messages import create_welcome_flex
        flex = create_welcome_flex()
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[FlexMessage(alt_text="ยินดีต้อนรับ / Welcome", contents=flex)],
            )
        )

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "text handled user=%s →%s elapsed_ms=%d",
        user_id,
        user_sessions.get(user_id, {}).get("state", "?"),
        elapsed_ms,
    )


# ── Image Message Handler ─────────────────────────────────────────────────────
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event: MessageEvent):
    from handlers.identity  import handle_policy_image
    from handlers.documents import handle_document_image

    user_id    = event.source.user_id
    message_id = event.message.id
    t0         = time.monotonic()

    if user_id not in user_sessions:
        user_sessions[user_id] = _new_session()

    session = user_sessions[user_id]
    state   = session.get("state", "idle")
    logger.info("image user=%s state=%s message_id=%s", user_id, state, message_id)

    try:
        headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
        url     = f"{LINE_DATA_API_HOST}/v2/bot/message/{message_id}/content"
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            image_bytes  = resp.content
            content_type = resp.headers.get("content-type", "image/jpeg")
    except Exception as exc:
        logger.error("Failed to download image %s: %s", message_id, exc)
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="❌ ไม่สามารถรับรูปภาพได้ กรุณาลองใหม่")],
                )
            )
        return

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if state in ("verifying_policy", "waiting_for_info"):
            handle_policy_image(line_bot_api, user_id, user_sessions, image_bytes)
        elif state in ("uploading_documents", "ready_to_submit", "awaiting_ownership"):
            handle_document_image(
                line_bot_api, user_id, user_sessions, image_bytes, content_type
            )
        else:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(
                        text="ℹ️ กรุณาพิมพ์ 'เคลม' เพื่อเริ่มขั้นตอน / Type 'claim' to start."
                    )],
                )
            )

    logger.info(
        "image handled user=%s elapsed_ms=%d",
        user_id,
        int((time.monotonic() - t0) * 1000),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Reviewer Dashboard  (FR-08)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/reviewer", response_class=HTMLResponse)
async def reviewer_dashboard(
    request: Request,
    status: Optional[str] = Query(None),
    claim_type: Optional[str] = Query(None),
):
    from storage.claim_store import list_all_claims

    allowed_statuses = {"Submitted", "Under Review", "Pending"}
    claims = list_all_claims(
        status_filter=status if status in allowed_statuses else None,
        type_filter=claim_type,
    )
    return templates.TemplateResponse(
        "reviewer.html",
        {
            "request": request,
            "claims": claims,
            "selected_status": status or "",
            "selected_type": claim_type or "",
            "all_statuses": list(allowed_statuses),
            "valid_transitions": VALID_TRANSITIONS,
        },
    )


@app.get("/reviewer/document")
async def reviewer_get_document(
    claim_id: str = Query(...),
    filename: str = Query(...),
):
    from storage.document_store import get_document_bytes

    data = get_document_bytes(claim_id, filename)
    if data is None:
        raise HTTPException(status_code=404, detail="Document not found")
    ext  = filename.rsplit(".", 1)[-1].lower()
    mime = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "pdf": "application/pdf",
    }.get(ext, "application/octet-stream")
    return Response(content=data, media_type=mime)


@app.post("/reviewer/useful")
async def reviewer_mark_useful(request: Request):
    from storage.claim_store import mark_document_useful

    body = await request.json()
    mark_document_useful(
        body.get("claim_id", ""),
        body.get("filename", ""),
        bool(body.get("useful", True)),
    )
    return {"ok": True}


@app.post("/reviewer/status")
async def reviewer_update_status(request: Request):
    from storage.claim_store import update_claim_status, get_claim_status

    body        = await request.json()
    claim_id    = body.get("claim_id", "")
    new_status  = body.get("status", "")
    memo        = body.get("memo", "")
    paid_amount = body.get("paid_amount")

    current = get_claim_status(claim_id)
    if not current:
        raise HTTPException(status_code=404, detail="Claim not found")

    allowed = VALID_TRANSITIONS.get(current.get("status", ""), [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition from '{current.get('status')}' to '{new_status}'",
        )

    update_claim_status(claim_id, new_status, memo=memo, paid_amount=paid_amount)
    logger.info("reviewer claim=%s %s→%s", claim_id, current.get("status"), new_status)
    return {"ok": True, "claim_id": claim_id, "new_status": new_status}


# ══════════════════════════════════════════════════════════════════════════════
# Manager Dashboard  (FR-09)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/manager", response_class=HTMLResponse)
async def manager_dashboard(request: Request):
    return templates.TemplateResponse("manager.html", {"request": request})


@app.get("/manager/data")
async def manager_data(
    date_from: Optional[str] = Query(None),
    date_to:   Optional[str] = Query(None),
):
    from storage.claim_store import list_all_claims

    claims = list_all_claims(date_from=date_from, date_to=date_to)
    status_counts: Dict[str, int] = {s: 0 for s in ALL_STATUSES}
    type_counts: Dict[str, int]   = {"CD": 0, "H": 0}
    daily_counts: Dict[str, int]  = {}

    for c in claims:
        st = c.get("status", "")
        if st in status_counts:
            status_counts[st] += 1
        ct = c.get("claim_type", "")
        if ct in type_counts:
            type_counts[ct] += 1
        try:
            date_part = c.get("claim_id", "").split("-")[1]
            day = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            daily_counts[day] = daily_counts.get(day, 0) + 1
        except (IndexError, AttributeError):
            pass

    return {
        "total": len(claims),
        "status_counts": status_counts,
        "type_counts": type_counts,
        "daily_counts": dict(sorted(daily_counts.items())),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Admin Dashboard  (FR-10)
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        "admin.html", {"request": request, "version": APP_VERSION}
    )


@app.post("/admin/loglevel")
async def admin_set_loglevel(request: Request):
    body  = await request.json()
    level = body.get("level", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise HTTPException(status_code=422, detail="Invalid log level")
    logging.getLogger().setLevel(level)
    logger.info("Admin changed log level to %s", level)
    return {"ok": True, "level": level}


@app.get("/admin/tokens")
async def admin_token_usage(month: Optional[str] = Query(None)):
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    token_file = os.path.join(DATA_DIR, "token_records", f"{month}.jsonl")
    if not os.path.exists(token_file):
        return {
            "month": month,
            "records": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0,
        }

    records: List[Dict] = []
    total_input = total_output = total_cost = 0.0
    try:
        with open(token_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    records.append(rec)
                    total_input  += rec.get("input_tokens",  0)
                    total_output += rec.get("output_tokens", 0)
                    total_cost   += rec.get("cost_usd", 0)
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass

    return {
        "month": month,
        "records": records[-100:],
        "total_input_tokens":  int(total_input),
        "total_output_tokens": int(total_output),
        "total_cost_usd": round(total_cost, 6),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting Uvicorn on port %d", port)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level=LOG_LEVEL.lower(),
        access_log=True,
    )
