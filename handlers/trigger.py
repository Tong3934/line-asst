"""
handlers/trigger.py — Claim-type detection and session initialisation.

Responsibilities:
  - Detect claim type from free-text keywords (FR-01.2 – FR-01.5)
  - Generate Claim ID (FR-01.6 – FR-01.7)
  - Create storage record for the new claim
  - Transition session to "verifying_policy"
"""

import logging
from typing import Dict

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

from constants import CD_KEYWORDS, H_KEYWORDS, TRIGGER_KEYWORDS, CANCEL_KEYWORDS
from storage.sequence import next_claim_id
from storage.claim_store import create_claim

logger = logging.getLogger(__name__)


def _detect_claim_type(text: str) -> str:
    """Detect claim type from free-text.

    Returns:
        "CD"        — car damage keywords detected
        "H"         — health keywords detected
        "ambiguous" — both sets matched
        "none"      — no keywords found
    """
    lower = text.lower()
    words = set(lower.split())
    cd_hit = any(kw in lower for kw in CD_KEYWORDS)
    h_hit  = any(kw in lower for kw in H_KEYWORDS)

    if cd_hit and h_hit:
        return "ambiguous"
    if cd_hit:
        return "CD"
    if h_hit:
        return "H"
    return "none"


def is_trigger(text: str) -> bool:
    """Return True if the message should start a new claim session."""
    lower = text.lower()
    if any(kw in lower for kw in TRIGGER_KEYWORDS):
        return True
    claim_type = _detect_claim_type(lower)
    return claim_type in ("CD", "H", "ambiguous")


def handle_trigger(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Detect claim type, create record, start session, reply to user.

    If the trigger is ambiguous, ask the user to pick a claim type.
    If the trigger is a direct keyword match, go straight to policy verification.
    """
    from flex_messages import create_claim_confirmed_flex, create_claim_type_selector_flex

    claim_type = _detect_claim_type(text)

    if claim_type == "ambiguous" or claim_type == "none":
        # Ask user to select CD or H
        flex = create_claim_type_selector_flex()
        user_sessions[user_id] = {"state": "detecting_claim_type"}
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[FlexMessage(alt_text="กรุณาเลือกประเภทการเคลม / Select claim type", contents=flex)],
            )
        )
        return

    # Known type — create claim immediately
    _start_claim(line_bot_api, event, user_id, user_sessions, claim_type)


def handle_claim_type_selection(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    text: str,
) -> None:
    """Handle quick-reply button press from claim type selector."""
    if "รถ" in text or "car" in text.lower() or text == "CD":
        _start_claim(line_bot_api, event, user_id, user_sessions, "CD")
    elif "สุขภาพ" in text or "health" in text.lower() or text == "H":
        _start_claim(line_bot_api, event, user_id, user_sessions, "H")
    else:
        # Show selector again
        from flex_messages import create_claim_type_selector_flex
        flex = create_claim_type_selector_flex()
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[FlexMessage(alt_text="กรุณาเลือกประเภทการเคลม", contents=flex)],
            )
        )


def _start_claim(
    line_bot_api: MessagingApi,
    event,
    user_id: str,
    user_sessions: Dict,
    claim_type: str,
) -> None:
    """Generate Claim ID, create storage record, send confirmation, advance to verifying_policy."""
    from flex_messages import create_claim_confirmed_flex, create_request_info_flex

    claim_id = next_claim_id(claim_type)
    create_claim(claim_id, claim_type, user_id)

    user_sessions[user_id] = {
        "state": "verifying_policy",
        "claim_id": claim_id,
        "claim_type": claim_type,
        "policy_info": None,
        "has_counterpart": None,
        "search_results": [],
        "uploaded_docs": {},
        "awaiting_ownership_for": None,
        "additional_info": None,
    }

    logger.info("Started claim %s for user (id suppressed)", claim_id)

    confirm_flex = create_claim_confirmed_flex(claim_id, claim_type)
    request_flex = create_request_info_flex()

    line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[
                FlexMessage(alt_text=f"Claim ID: {claim_id}", contents=confirm_flex),
                FlexMessage(alt_text="กรุณายืนยันตัวตน / Identity verification", contents=request_flex),
            ],
        )
    )
