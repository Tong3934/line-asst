"""
handlers/documents.py — Document upload loop: categorise → extract → ownership → checklist.

Responsibilities:
  - Accept image in "uploading_documents" state
  - Categorise → reject unknowns
  - Extract structured fields
  - For driving license in with-counterpart CD claim → ownership question
  - Save image and extracted data to storage
  - Update session uploaded_docs and show checklist → when complete advance to ready_to_submit
  - Handle counterpart and ownership text inputs
"""

import logging
from typing import Dict, Optional

from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    FlexMessage,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)

from constants import REQUIRED_DOCS, OPTIONAL_DOCS
from storage import claim_store, document_store

logger = logging.getLogger(__name__)


# ── Counterpart question (CD) ─────────────────────────────────────────────────

def handle_counterpart_answer(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Process มีคู่กรณี / ไม่มีคู่กรณี answer."""
    from flex_messages import create_document_checklist_flex

    session = user_sessions[user_id]
    claim_id = session.get("claim_id")

    if text not in ("มีคู่กรณี", "ไม่มีคู่กรณี"):
        qr = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="✅ มีคู่กรณี", text="มีคู่กรณี")),
            QuickReplyItem(action=MessageAction(label="❌ ไม่มีคู่กรณี", text="ไม่มีคู่กรณี")),
        ])
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text="❌ กรุณาเลือกจากปุ่ม / Please choose from buttons:",
                    quick_reply=qr,
                )],
            )
        )
        return

    session["has_counterpart"] = text
    session["state"] = "uploading_documents"

    # Update stored claim with counterpart info
    if claim_id:
        claim_store.update_claim_status(claim_id, "Draft", memo=f"has_counterpart={text}")

    checklist_flex = create_document_checklist_flex("CD", text, session.get("uploaded_docs", {}))
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[FlexMessage(
                alt_text="รายการเอกสารที่ต้องการ / Required documents",
                contents=checklist_flex,
            )],
        )
    )


# ── Ownership confirmation (CD with-counterpart) ──────────────────────────────

def handle_ownership_answer(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Assign pending driving license to customer or other-party slot."""
    from flex_messages import create_document_checklist_flex, create_doc_received_flex

    session = user_sessions[user_id]
    claim_id = session.get("claim_id")
    uploaded = session.get("uploaded_docs", {})

    if "ของฉัน" in text or "ฝ่ายเรา" in text:
        target_key = "driving_license_customer"
    elif "คู่กรณี" in text or "อีกฝ่าย" in text:
        target_key = "driving_license_other_party"
    else:
        qr = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="ของฉัน (ฝ่ายเรา)", text="ของฉัน (ฝ่ายเรา)")),
            QuickReplyItem(action=MessageAction(label="คู่กรณี (อีกฝ่าย)", text="คู่กรณี (อีกฝ่าย)")),
        ])
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="⚠️ กรุณาเลือก / Please select:", quick_reply=qr)],
            )
        )
        return

    # Check for duplicate
    if target_key in uploaded:
        qr = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="ของฉัน (ฝ่ายเรา)", text="ของฉัน (ฝ่ายเรา)")),
            QuickReplyItem(action=MessageAction(label="คู่กรณี (อีกฝ่าย)", text="คู่กรณี (อีกฝ่าย)")),
        ])
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=(
                        f"⚠️ มีใบขับขี่ฝั่ง '{target_key}' อยู่แล้ว / "
                        f"Driving license for '{target_key}' already uploaded.\n"
                        "กรุณาเลือกฝั่งที่ถูกต้อง / Please select the correct side:"
                    ),
                    quick_reply=qr,
                )],
            )
        )
        return

    # Retrieve pending data (may be a dict or a plain filename string from legacy sessions)
    pending_raw = session.pop("awaiting_ownership_for", None)
    if not pending_raw:
        logger.warning("No pending ownership data for user in claim")
        session["state"] = "uploading_documents"
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="⚠️ ไม่พบข้อมูลรอยืนยัน / No pending data. Please re-upload.")],
            )
        )
        return

    if isinstance(pending_raw, dict):
        filename   = pending_raw["filename"]
        fields     = pending_raw.get("fields", {})
        image_bytes = pending_raw.get("image_bytes", b"")
    else:
        # Legacy / test: awaiting_ownership_for is a plain filename string
        filename    = str(pending_raw)
        fields      = {}
        image_bytes = b""

    # Rename / re-save with correct category key
    if claim_id:
        final_filename = document_store.save_document(
            claim_id, target_key, image_bytes, ext=filename.rsplit(".", 1)[-1]
        )
        claim_store.add_document_to_claim(claim_id, target_key, final_filename)
        claim_store.update_extracted_data(claim_id, target_key, fields)
    else:
        final_filename = filename

    uploaded[target_key] = final_filename
    session["uploaded_docs"] = uploaded
    session["state"] = "uploading_documents"

    missing = _missing_docs(session)
    checklist_flex = create_doc_received_flex(target_key, fields, missing)
    messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=checklist_flex)]

    if not missing:
        session["state"] = "ready_to_submit"
        from flex_messages import create_submit_prompt_flex
        submit_flex = create_submit_prompt_flex(claim_id, len(uploaded))
        messages.append(FlexMessage(alt_text="พร้อมส่งคำร้อง / Ready to submit", contents=submit_flex))

    line_bot_api.reply_message(
        ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
    )


# ── Image upload processing ───────────────────────────────────────────────────

def handle_document_image(
    line_bot_api: MessagingApi,
    user_id: str,
    user_sessions: Dict,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> None:
    """Categorise → extract → ownership or save → update checklist. Uses push."""
    from ai.categorise import categorise_document
    from ai.extract import extract_fields
    from flex_messages import (
        create_doc_received_flex,
        create_ownership_question_flex,
        create_submit_prompt_flex,
        create_document_checklist_flex,
    )

    session = user_sessions[user_id]
    claim_id   = session.get("claim_id")
    claim_type = session.get("claim_type", "CD")
    uploaded = session.setdefault("uploaded_docs", {})

    ext = content_type.split("/")[-1].replace("jpeg", "jpg")

    # Step 1 — Categorise
    category = categorise_document(image_bytes)
    if category == "unknown":
        _required = _required_doc_keys(session)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(
                    text=(
                        "❌ ไม่รู้จักเอกสาร / Unknown document type.\n"
                        f"เอกสารที่ต้องการ / Required: {', '.join(_required)}\n\n"
                        "กรุณาส่งรูปใหม่ / Please resend a correct document photo."
                    )
                )],
            )
        )
        return

    # Step 2 — Extract fields
    fields = extract_fields(image_bytes, category)

    # Step 3 — driving_license in with-counterpart CD claim → ask ownership
    if category == "driving_license" and session.get("has_counterpart") == "มีคู่กรณี":
        # Temporarily save image bytes in session for later assignment
        tmp_filename = f"driving_license_pending.{ext}"
        session["awaiting_ownership_for"] = {
            "filename": tmp_filename,
            "fields": fields,
            "image_bytes": image_bytes,
        }
        session["state"] = "awaiting_ownership"

        name = fields.get("full_name_th") or fields.get("full_name_en") or "ไม่ทราบชื่อ"
        ownership_flex = create_ownership_question_flex(name)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[FlexMessage(alt_text="ใบขับขี่นี้ของใคร? / Whose license?", contents=ownership_flex)],
            )
        )
        return

    # Step 4 — Determine storage key
    if category == "driving_license":
        # No-counterpart CD or Health (shouldn't reach this for H, but safe)
        storage_key = "driving_license_customer"
    elif category in ("vehicle_damage_photo",):
        # Count existing damage photos for list naming
        existing_count = sum(1 for k in uploaded if k.startswith("vehicle_damage_photo"))
        storage_key = f"vehicle_damage_photo_{existing_count + 1}"
    elif category == "receipt":
        existing_count = sum(1 for k in uploaded if k.startswith("receipt"))
        storage_key = f"receipt_{existing_count + 1}"
    else:
        storage_key = category

    # Step 5 — Save
    if claim_id:
        filename = document_store.save_document(claim_id, storage_key, image_bytes, ext=ext)
        claim_store.add_document_to_claim(claim_id, storage_key, filename)
        claim_store.update_extracted_data(claim_id, storage_key, fields)
    else:
        filename = f"{storage_key}.{ext}"

    uploaded[storage_key] = filename
    session["uploaded_docs"] = uploaded

    # Step 6 — Update checklist, check completion
    missing = _missing_docs(session)
    doc_flex = create_doc_received_flex(storage_key, fields, missing)
    messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=doc_flex)]

    if not missing:
        session["state"] = "ready_to_submit"
        submit_flex = create_submit_prompt_flex(claim_id, len(uploaded))
        messages.append(FlexMessage(alt_text="พร้อมส่งคำร้อง / Ready to submit", contents=submit_flex))

    line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _required_doc_keys(session: Dict):
    """Return list of required doc keys for this session's claim type / counterpart."""
    claim_type = session.get("claim_type", "CD")
    has_counterpart = session.get("has_counterpart")
    reqs = REQUIRED_DOCS.get(claim_type, {})
    if claim_type == "CD":
        return reqs.get(has_counterpart, reqs.get("ไม่มีคู่กรณี", []))
    return reqs.get(None, [])


def _missing_docs(session: Dict):
    """Return list of required doc keys not yet in uploaded_docs."""
    required = _required_doc_keys(session)
    uploaded = session.get("uploaded_docs", {})

    missing = []
    for key in required:
        # Handle list-type keys: vehicle_damage_photo counts as satisfied if any _1, _2… exists
        base = key.split("_")[:-1] if key[-1].isdigit() else key.split("_")
        base_str = "_".join(base) if isinstance(base, list) else base
        if key in uploaded:
            continue
        # Check for numbered variants (vehicle_damage_photo_1, receipt_1, etc.)
        if any(u.startswith(key) or u.startswith(base_str) for u in uploaded):
            continue
        missing.append(key)
    return missing
