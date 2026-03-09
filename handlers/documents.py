"""
handlers/documents.py — Document upload loop: categorise → extract → ownership → checklist.

v2.2 Phased CD upload:
  Phase 1 (uploading_damage_photos):  Accept damage/location photos only
  Phase 2 (confirming_claim):         Customer confirms to start claim process
  Phase 3 (uploading_identity_docs):  Accept driving license(s) + vehicle registration

Health (H) claims use the original single-phase uploading_documents flow.

Responsibilities:
  - Accept images in the appropriate upload state
  - Categorise → reject unknowns / wrong-phase documents
  - Extract structured fields
  - For driving license in with-counterpart CD claim → ownership question
  - Save image and extracted data to storage
  - Update session uploaded_docs and show checklist → when complete advance to next phase
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

from constants import REQUIRED_DOCS, OPTIONAL_DOCS, PHASE1_CATEGORIES, PHASE3_CATEGORIES
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
    """Process มีคู่กรณี / ไม่มีคู่กรณี answer → transition to uploading_damage_photos."""
    from flex_messages import create_damage_photo_request_flex

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
    session["state"] = "uploading_damage_photos"
    session["uploaded_docs"] = {}

    # Update stored claim with counterpart info
    if claim_id:
        claim_store.update_claim_status(claim_id, "Draft", memo=f"has_counterpart={text}")

    # Phase 1: Ask for damage photos
    damage_flex = create_damage_photo_request_flex()
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                TextMessage(text=f"รับทราบค่ะ ({text})\n\n📸 กรุณาส่งรูปถ่ายความเสียหายของรถก่อนค่ะ"),
                FlexMessage(
                    alt_text="ส่งรูปความเสียหาย / Send damage photos",
                    contents=damage_flex,
                ),
            ],
        )
    )


# ── Phase 1: Damage photo upload (CD only) ────────────────────────────────────

def handle_damage_photo_image(
    line_bot_api: MessagingApi,
    user_id: str,
    user_sessions: Dict,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> None:
    """Phase 1 — Accept damage/location photos only. Uses push."""
    from ai.categorise import categorise_document
    from ai.extract import extract_fields
    from flex_messages import (
        create_doc_received_flex,
        create_confirm_claim_flex,
    )

    session = user_sessions[user_id]
    claim_id = session.get("claim_id")
    uploaded = session.setdefault("uploaded_docs", {})
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")

    # Step 1 — Categorise
    category = categorise_document(image_bytes)

    # Reject non-damage documents in Phase 1
    if category == "unknown" or category not in PHASE1_CATEGORIES:
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(
                    text=(
                        "📸 ขั้นตอนนี้รับเฉพาะรูปความเสียหายของรถค่ะ\n"
                        "Phase 1: Please send car damage photos only.\n\n"
                        "เอกสารอื่น (ใบขับขี่, ทะเบียนรถ) จะส่งในขั้นตอนถัดไป"
                    )
                )],
            )
        )
        return

    # Step 2 — Extract fields
    fields = extract_fields(image_bytes, category)

    # Step 3 — Determine storage key
    if category == "vehicle_damage_photo":
        existing_count = sum(1 for k in uploaded if k.startswith("vehicle_damage_photo"))
        storage_key = f"vehicle_damage_photo_{existing_count + 1}"
    else:
        storage_key = category  # vehicle_location_photo

    # Step 4 — Save
    if claim_id:
        filename = document_store.save_document(claim_id, storage_key, image_bytes, ext=ext)
        claim_store.add_document_to_claim(claim_id, storage_key, filename)
        claim_store.update_extracted_data(claim_id, storage_key, fields)
    else:
        filename = f"{storage_key}.{ext}"

    uploaded[storage_key] = filename
    session["uploaded_docs"] = uploaded

    # Step 5 — (Removed immediate analysis, now waits for user to click Start Analysis)
    
    # Step 6 — Show acknowledgement
    damage_count = sum(1 for k in uploaded if k.startswith("vehicle_damage_photo"))

    if category in ("vehicle_damage_photo", "vehicle_location_photo"):
        from flex_messages import create_damage_photo_received_flex
        doc_flex = create_damage_photo_received_flex(fields, damage_count)
        messages = [FlexMessage(alt_text=f"รับรูปความเสียหาย ({damage_count}) รูป", contents=doc_flex)]
    else:
        doc_flex = create_doc_received_flex(storage_key, fields, [])
        messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=doc_flex)]

    line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))


def handle_start_damage_analysis(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
) -> None:
    """Triggered when user clicks 'เริ่มทำการวิเคราะห์'. Runs analysis on all collected photos."""
    from flex_messages import create_confirm_claim_flex
    import os

    session = user_sessions[user_id]
    uploaded = session.get("uploaded_docs", {})
    claim_id = session.get("claim_id")
    
    damage_keys = [k for k in uploaded if k.startswith("vehicle_damage_photo")]
    
    if not damage_keys:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="❌ ยังไม่มีรูปความเสียหาย กรุณาส่งรูปเข้ามาก่อนค่ะ")]
            )
        )
        return

    # Read bytes from storage
    image_bytes_list = []
    for k in damage_keys:
        filename = uploaded[k]
        try:
            if claim_id:
                filepath = document_store.get_document_path(claim_id, filename)
            else:
                filepath = filename
            with open(filepath, "rb") as fh:
                image_bytes_list.append(fh.read())
        except Exception as e:
            logger.error("Failed to read image %s: %s", filename, e)
            
    if not image_bytes_list:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="❌ ไม่สามารถอ่านไฟล์รูปได้ กรุณาลองส่งใหม่อีกครั้ง")]
            )
        )
        return

    # Run AI on all images
    _run_damage_analysis(line_bot_api, user_id, session, image_bytes_list)
    
    # After analysis is done, transition to Phase 2 confirmation
    session["state"] = "confirming_claim"
    confirm_flex = create_confirm_claim_flex(len(damage_keys))
    line_bot_api.push_message(
        PushMessageRequest(
            to=user_id, 
            messages=[FlexMessage(alt_text="ยืนยันเริ่มเคลม? / Confirm claim?", contents=confirm_flex)]
        )
    )

# ── Phase 2: Confirm claim (CD only — text handler) ──────────────────────────

def handle_confirm_claim(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Phase 2 — Customer confirms to start claim process → transition to uploading_identity_docs."""
    from flex_messages import create_identity_doc_request_flex

    session = user_sessions[user_id]
    uploaded = session.get("uploaded_docs", {})

    if text in ("ยืนยัน", "confirm", "Confirm"):
        session["state"] = "uploading_identity_docs"

        has_counterpart = session.get("has_counterpart", "ไม่มีคู่กรณี")
        identity_flex = create_identity_doc_request_flex(has_counterpart, uploaded)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text="✅ ยืนยันแล้วค่ะ! / Confirmed!\n\n📄 กรุณาส่งเอกสารยืนยันตัวตนค่ะ"),
                    FlexMessage(
                        alt_text="ส่งเอกสารยืนยันตัวตน / Send identity documents",
                        contents=identity_flex,
                    ),
                ],
            )
        )
        return

    # Not a confirm — check if they're sending more damage photos (allow it)
    # Otherwise remind them to confirm
    qr = QuickReply(items=[
        QuickReplyItem(action=MessageAction(label="✅ ยืนยัน / Confirm", text="ยืนยัน")),
    ])
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(
                text=(
                    "กรุณากดปุ่ม 'ยืนยัน' เพื่อดำเนินการต่อ\n"
                    "Please tap 'ยืนยัน' to proceed.\n\n"
                    "หรือส่งรูปความเสียหายเพิ่มเติมได้ค่ะ"
                ),
                quick_reply=qr,
            )],
        )
    )


# ── Phase 3: Identity document upload (CD only) ──────────────────────────────

def handle_identity_doc_image(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> None:
    """Phase 3 — Accept driving license(s) + vehicle registration only. Uses push."""
    from ai.categorise import categorise_document
    from ai.extract import extract_fields
    from flex_messages import (
        create_doc_received_flex,
        create_ownership_question_flex,
        create_submit_prompt_flex,
        create_identity_doc_request_flex,
    )

    session = user_sessions[user_id]
    claim_id = session.get("claim_id")
    uploaded = session.setdefault("uploaded_docs", {})
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")

    message = getattr(event, "message", None)
    image_set = getattr(message, "image_set", None)
    if image_set and getattr(image_set, "index", 1) > 1:
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text="⏳ กำลังวิเคราะห์เอกสารถัดไป กรุณารอสักครู่...")]
            )
        )

    # Step 1 — Categorise
    category = categorise_document(image_bytes)

    # Reject non-identity documents in Phase 3
    if category == "unknown" or category not in PHASE3_CATEGORIES:
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(
                    text=(
                        "📄 ขั้นตอนนี้รับเฉพาะใบขับขี่และสมุดเล่มทะเบียนรถค่ะ\n"
                        "Phase 3: Please send driving license or vehicle registration only.\n\n"
                        "รูปความเสียหายได้รับเรียบร้อยแล้ว"
                    )
                )],
            )
        )
        return

    # Step 2 — Extract fields
    fields = extract_fields(image_bytes, category)

    # Step 3 — Driving license in with-counterpart claim → ask ownership
    if category == "driving_license" and session.get("has_counterpart") == "มีคู่กรณี":
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

    # Step 4 — Determine storage key (no-counterpart: always customer)
    if category == "driving_license":
        storage_key = "driving_license_customer"
    else:
        storage_key = category  # vehicle_registration

    # Step 5 — Save
    if claim_id:
        filename = document_store.save_document(claim_id, storage_key, image_bytes, ext=ext)
        claim_store.add_document_to_claim(claim_id, storage_key, filename)
        claim_store.update_extracted_data(claim_id, storage_key, fields)
    else:
        filename = f"{storage_key}.{ext}"

    uploaded[storage_key] = filename
    session["uploaded_docs"] = uploaded

    # Step 6 — Check Phase 3 completion
    missing = _missing_identity_docs(session)
    doc_flex = create_doc_received_flex(storage_key, fields, missing)
    messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=doc_flex)]

    if not missing:
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))
        from handlers.submit import handle_submit_request
        handle_submit_request(line_bot_api, event, user_id, user_sessions)
        return

    line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))


# ── Ownership confirmation (CD with-counterpart) ──────────────────────────────

def handle_ownership_answer(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Assign pending driving license to customer or other-party slot."""
    from flex_messages import create_doc_received_flex, create_submit_prompt_flex

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

    # Retrieve pending data
    pending_raw = session.pop("awaiting_ownership_for", None)
    if not pending_raw:
        logger.warning("No pending ownership data for user in claim")
        session["state"] = "uploading_identity_docs"
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="⚠️ ไม่พบข้อมูลรอยืนยัน / No pending data. Please re-upload.")],
            )
        )
        return

    if isinstance(pending_raw, dict):
        filename = pending_raw["filename"]
        fields = pending_raw.get("fields", {})
        image_bytes = pending_raw.get("image_bytes", b"")
    else:
        filename = str(pending_raw)
        fields = {}
        image_bytes = b""

    # Save with correct category key
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
    session["state"] = "uploading_identity_docs"

    missing = _missing_identity_docs(session)
    doc_flex = create_doc_received_flex(target_key, fields, missing)
    messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=doc_flex)]

    if not missing:
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))
        from handlers.submit import handle_submit_request
        handle_submit_request(line_bot_api, event, user_id, user_sessions)
        return

    line_bot_api.reply_message(
        ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
    )


# ── Original single-phase upload (Health claims) ─────────────────────────────

def handle_document_image(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    image_bytes: bytes,
    content_type: str = "image/jpeg",
) -> None:
    """Categorise → extract → ownership or save → update checklist. Uses push.
    Used for Health (H) claims in uploading_documents state."""
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

    message = getattr(event, "message", None)
    image_set = getattr(message, "image_set", None)
    if image_set and getattr(image_set, "index", 1) > 1:
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text="⏳ กำลังวิเคราะห์เอกสารถัดไป กรุณารอสักครู่...")]
            )
        )

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
        storage_key = "driving_license_customer"
    elif category in ("vehicle_damage_photo",):
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

    # Step 5b — Run damage analysis for vehicle_damage_photo
    if category == "vehicle_damage_photo":
        _run_damage_analysis(line_bot_api, user_id, session, image_bytes)

    # Step 6 — Update checklist, check completion
    missing = _missing_docs(session)
    doc_flex = create_doc_received_flex(storage_key, fields, missing)
    messages = [FlexMessage(alt_text="เอกสารที่ได้รับ / Document received", contents=doc_flex)]

    if not missing:
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))
        from handlers.submit import handle_submit_request
        handle_submit_request(line_bot_api, event, user_id, user_sessions)
        return

    line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_damage_analysis(line_bot_api, user_id, session, image_bytes):
    """Run AI damage analysis and send result to user."""
    from ai.analyse_damage import analyse_damage
    from flex_messages import create_analysis_result_flex
    from claim_engine import extract_phone_from_response

    line_bot_api.push_message(
        PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text="⏳ กำลังวิเคราะห์ความเสียหาย...\n\nกรุณารอสักครู่ (ประมาณ 10-20 วินาที)")],
        )
    )

    policy_info = session.get("policy_info", {})
    has_counterpart = session.get("has_counterpart")
    try:
        analysis_result = analyse_damage(
            image_bytes=image_bytes,
            policy_info=policy_info,
            additional_info=None,
            has_counterpart=has_counterpart,
        )
        phone_number = extract_phone_from_response(analysis_result) or policy_info.get("phone")

        if phone_number:
            analysis_flex = create_analysis_result_flex(
                summary_text=analysis_result,
                phone_number=phone_number,
                insurance_company=policy_info.get("insurance_company", ""),
                claim_status="unknown",
            )
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[FlexMessage(alt_text="ผลการวิเคราะห์ความเสียหาย / Damage Analysis", contents=analysis_flex)],
                )
            )
        else:
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[TextMessage(text=analysis_result)],
                )
            )
    except Exception as exc:
        logger.error("Damage analysis error: %s", exc)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=f"⚠️ ไม่สามารถวิเคราะห์ความเสียหายได้ / Analysis error: {exc}")],
            )
        )


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
        base = key.split("_")[:-1] if key[-1].isdigit() else key.split("_")
        base_str = "_".join(base) if isinstance(base, list) else base
        if key in uploaded:
            continue
        if any(u.startswith(key) or u.startswith(base_str) for u in uploaded):
            continue
        missing.append(key)
    return missing


def _missing_identity_docs(session: Dict):
    """Return list of required identity doc keys not yet uploaded (Phase 3 only).
    Checks driving licenses + vehicle registration, NOT damage photos
    (those were already collected in Phase 1)."""
    has_counterpart = session.get("has_counterpart")
    required = ["driving_license_customer", "vehicle_registration"]
    if has_counterpart == "มีคู่กรณี":
        required.insert(1, "driving_license_other_party")

    uploaded = session.get("uploaded_docs", {})
    return [key for key in required if key not in uploaded]
