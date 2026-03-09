"""
handlers/identity.py — Policy verification by typed CID, plate, name, or photo.

Responsibilities (FR-02):
  - Accept typed 13-digit CID or license plate (text)
  - Accept photo of ID card or driving license (AI OCR)
  - Look up policy in mock_data (or future DB/API)
  - On single match: show policy card → advance to waiting_for_counterpart (CD) or uploading_documents (H)
  - On multiple matches: show vehicle selection carousel
  - On failure: prompt retry
"""

import logging
import re
from typing import Dict, List, Optional

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

from mock_data import (
    search_policies_by_cid,
    search_policies_by_name,
    search_policies_by_plate,
    search_health_policies_by_cid,
)
from storage.claim_store import update_claim_status

logger = logging.getLogger(__name__)


def handle_policy_text(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Handle typed CID / plate / name in verifying_policy state."""
    session = user_sessions[user_id]
    claim_type = session.get("claim_type", "CD")
    text_clean = text.replace("-", "").replace(" ", "")

    if re.match(r"^\d{13}$", text_clean):
        if claim_type == "CD":
            policies = search_policies_by_cid(text_clean)
        else:
            policies = search_health_policies_by_cid(text_clean)
    elif claim_type == "CD":
        policy = search_policies_by_plate(text)
        policies = [policy] if policy else search_policies_by_name(text)
    else:
        policies = search_health_policies_by_cid(text_clean) or search_policies_by_name(text)

    _process_search_result(line_bot_api, event, user_id, user_sessions, policies, use_push=False)


def handle_policy_image(
    line_bot_api: MessagingApi,
    user_id: str,
    user_sessions: Dict,
    image_bytes: bytes,
) -> None:
    """Handle photo OCR for policy verification (uses push because reply token consumed)."""
    from ai.ocr import extract_id_from_image

    session = user_sessions[user_id]
    claim_type = session.get("claim_type", "CD")

    info = extract_id_from_image(image_bytes)
    logger.info("OCR result type=%s (value suppressed)", info.get("type"))

    if info["type"] in ("id_card", "driving_license") and info.get("value"):
        cid = info["value"]
        if claim_type == "CD":
            policies = search_policies_by_cid(cid)
        else:
            policies = search_health_policies_by_cid(cid)
    elif info["type"] == "license_plate" and info.get("value") and claim_type == "CD":
        p = search_policies_by_plate(info["value"])
        policies = [p] if p else []
    else:
        # push failure
        from linebot.v3.messaging import PushMessageRequest
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(
                    text=(
                        "❌ ไม่พบข้อมูลในรูปภาพ\n"
                        "กรุณาส่งรูปบัตรประชาชน หรือพิมพ์เลขบัตร 13 หลัก\n\n"
                        "❌ Could not read image.\n"
                        "Please send a clear ID card photo or type your 13-digit ID number."
                    )
                )],
            )
        )
        return

    _process_search_result(line_bot_api, None, user_id, user_sessions, policies, use_push=True)


def handle_vehicle_selection(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Handle 'เลือกทะเบียน {plate}' quick-reply in waiting_for_vehicle_selection state."""
    plate = text.replace("เลือกทะเบียน ", "").strip()
    policies = user_sessions[user_id].get("search_results", [])
    policy_info = next((p for p in policies if p.get("plate") == plate or p.get("vehicle_plate") == plate), None)

    if not policy_info:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text="❌ ไม่พบทะเบียนที่เลือก กรุณาเลือกอีกครั้ง / Vehicle not found. Please try again.")],
            )
        )
        return

    _apply_single_policy(line_bot_api, event, user_id, user_sessions, policy_info, use_push=False)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _process_search_result(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    policies: List[Dict],
    use_push: bool = False,
) -> None:
    if not policies:
        msg = TextMessage(
            text=(
                "❌ ไม่พบข้อมูลกรมธรรม์ กรุณาตรวจสอบข้อมูลอีกครั้ง\n\n"
                "❌ Policy not found. Please check your information and try again."
            )
        )
        _send(line_bot_api, event, user_id, [msg], use_push)
        return

    if len(policies) > 1:
        from flex_messages import create_vehicle_selection_flex
        user_sessions[user_id]["state"] = "waiting_for_vehicle_selection"
        user_sessions[user_id]["search_results"] = policies
        flex = create_vehicle_selection_flex(policies)
        msg = FlexMessage(alt_text="กรุณาเลือกรถยนต์ / Select vehicle", contents=flex)
        _send(line_bot_api, event, user_id, [msg], use_push)
    else:
        _apply_single_policy(line_bot_api, event, user_id, user_sessions, policies[0], use_push)


def _apply_single_policy(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    policy_info: Dict,
    use_push: bool,
) -> None:
    """Apply single found policy: update session, show policy card, ask next step."""
    from flex_messages import (
        create_policy_info_flex,
        create_health_policy_info_flex,
        create_document_checklist_flex,
    )

    session = user_sessions[user_id]
    claim_type = session.get("claim_type", "CD")
    claim_id   = session.get("claim_id", "")

    session["policy_info"] = policy_info

    # Check policy status
    status = policy_info.get("status", "active")
    if status == "expired":
        msg = TextMessage(
            text=(
                f"⚠️ กรมธรรม์หมดอายุ / Policy expired.\n"
                f"กรุณาติดต่อ {policy_info.get('insurance_company', '')} เพื่อต่ออายุ\n\n"
                "Please contact your insurer to renew."
            )
        )
        _send(line_bot_api, event, user_id, [msg], use_push)
        return
    if status != "active":
        msg = TextMessage(text="⚠️ กรมธรรม์ไม่ได้ใช้งาน / Policy inactive. Contact your insurer.")
        _send(line_bot_api, event, user_id, [msg], use_push)
        return

    messages = []

    if claim_type == "CD":
        flex_policy = create_policy_info_flex(policy_info)
        messages.append(FlexMessage(alt_text="พบข้อมูลกรมธรรม์ / Policy found", contents=flex_policy))

        # Ask counterpart question
        qr = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="✅ มีคู่กรณี", text="มีคู่กรณี")),
            QuickReplyItem(action=MessageAction(label="❌ ไม่มีคู่กรณี", text="ไม่มีคู่กรณี")),
        ])
        messages.append(TextMessage(
            text=(
                "❓ มีคู่กรณีหรือไม่? / Is there a counterpart vehicle?\n"
                "กรุณาเลือก / Please select:"
            ),
            quick_reply=qr,
        ))
        session["state"] = "waiting_for_counterpart"

    else:  # Health
        flex_policy = create_health_policy_info_flex(policy_info)
        messages.append(FlexMessage(alt_text="พบข้อมูลกรมธรรม์สุขภาพ / Health policy found", contents=flex_policy))

        # Go straight to uploading documents
        checklist_flex = create_document_checklist_flex("H", None, {})
        messages.append(FlexMessage(
            alt_text="กรุณาอัปโหลดเอกสาร / Please upload documents",
            contents=checklist_flex,
        ))
        session["state"] = "uploading_documents"

    _send(line_bot_api, event, user_id, messages, use_push)


def _send(line_bot_api, event, user_id, messages, use_push):
    if use_push:
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))
    else:
        line_bot_api.reply_message(
            ReplyMessageRequest(reply_token=event.reply_token, messages=messages)
        )
