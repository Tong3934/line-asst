"""
handlers/submit.py — Claim completeness check and submission.

Responsibilities:
  - Validate all required documents are present (FR-07.2)
  - Update claim status to "Submitted" with timestamp (FR-07.5)
  - Generate summary.md via AI (OQ-5 default: on submission)
  - Send Claim ID confirmation to customer (FR-07.6)
"""

import logging
from datetime import datetime, timezone
from typing import Dict

from linebot.v3.messaging import (
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    FlexMessage,
    TextMessage,
)

from storage import claim_store
from handlers.documents import _missing_docs

logger = logging.getLogger(__name__)


def handle_submit_request(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
) -> None:
    """Validate completeness → persist → send confirmation."""
    from flex_messages import create_submission_confirmed_flex

    session = user_sessions[user_id]
    claim_id = session.get("claim_id", "")

    # Re-validate completeness
    missing = _missing_docs(session)
    if missing:
        missing_th = {
            "driving_license_customer": "ใบขับขี่ (ของคุณ)",
            "driving_license_other_party": "ใบขับขี่ (คู่กรณี)",
            "vehicle_registration": "เล่มทะเบียนรถ",
            "vehicle_damage_photo": "รูปความเสียหาย",
            "citizen_id_card": "บัตรประชาชน",
            "medical_certificate": "ใบรับรองแพทย์",
            "itemised_bill": "ใบแจงค่าใช้จ่าย",
            "receipt": "ใบเสร็จรับเงิน",
        }
        missing_list = "\n".join(f"  • {missing_th.get(d, d)}" for d in missing)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(
                    text=(
                        "⚠️ ยังไม่ครบเอกสาร / Documents still missing:\n"
                        f"{missing_list}\n\n"
                        "กรุณาอัปโหลดให้ครบ / Please upload all required documents."
                    )
                )],
            )
        )
        return

    # Mark submitted
    submitted_at = datetime.now(timezone.utc).isoformat()
    claim_store.update_claim_status(
        claim_id,
        status="Submitted",
        submitted_at=submitted_at,
    )

    # Generate AI summary (async-like — runs in same thread; acceptable for PoC)
    _generate_summary(claim_id, session)

    session["state"] = "submitted"
    logger.info("Claim %s submitted", claim_id)

    confirm_flex = create_submission_confirmed_flex(claim_id)
    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[FlexMessage(alt_text=f"ส่งคำร้องสำเร็จ / Claim {claim_id} submitted", contents=confirm_flex)],
        )
    )


def _generate_summary(claim_id: str, session: Dict) -> None:
    """Generate a markdown claim summary via AI and save to storage."""
    try:
        from ai import call_gemini
        from storage.claim_store import get_extracted_data, save_summary
        import json

        data = get_extracted_data(claim_id)
        policy = session.get("policy_info", {})
        claim_type = session.get("claim_type", "CD")
        has_counterpart = session.get("has_counterpart", "N/A")

        prompt = f"""Generate a concise bilingual (Thai + English) claim summary in Markdown.
Claim ID: {claim_id}
Type: {claim_type}
Has counterpart: {has_counterpart}
Policy number: {policy.get('policy_number', 'N/A')}
Extracted data: {json.dumps(data, ensure_ascii=False, indent=2)[:2000]}

Format:
# ข้อมูลสรุปการเคลม / Claim Summary
## {claim_id}
…sections…
"""
        summary_text = call_gemini("generate_summary", prompt)
        save_summary(claim_id, summary_text)
        logger.info("Summary saved for claim %s", claim_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Summary generation failed for %s: %s", claim_id, exc)
