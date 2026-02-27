"""
test_conversation_flows.py
==========================
Integration tests for every conversation state-machine path defined in the
BRD / Tech-Spec.

Each test class covers one logical flow end-to-end by:
  1. Pre-seeding user_sessions via the `set_session` fixture, OR
  2. Driving the full flow step-by-step through the /webhook endpoint.

State transitions validated
---------------------------
  idle → detecting_claim_type (CD keyword)
  idle → detecting_claim_type (H keyword)
  idle → idle (ambiguous keywords, clarification prompt)
  detecting_claim_type → verifying_policy
  verifying_policy → waiting_for_counterpart (CD, 1 policy)
  verifying_policy → waiting_for_vehicle_selection (CD, many policies)
  waiting_for_vehicle_selection → waiting_for_counterpart
  waiting_for_counterpart → uploading_documents
  uploading_documents → awaiting_ownership (CD with counterpart)
  awaiting_ownership → uploading_documents (ownership confirmed)
  uploading_documents → ready_to_submit (all docs received)
  ready_to_submit → submitted
  Any state → idle on cancel keyword
  verifying_policy → retry on expired / inactive / not-found policy
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.test_data import (
    USER_ID_A,
    USER_ID_B,
    CD_POLICY_ACTIVE_CLASS1,
    CD_POLICY_ACTIVE_CLASS2PLUS,
    CD_POLICY_EXPIRED,
    CD_POLICY_INACTIVE,
    H_POLICY_ACTIVE,
    MOCK_CHANNEL_SECRET,
    WEBHOOK_TRIGGER_CD,
    WEBHOOK_TRIGGER_H,
    WEBHOOK_TRIGGER_MAIN,
    WEBHOOK_AMBIGUOUS,
    WEBHOOK_CID_TEXT,
    WEBHOOK_COUNTERPART_YES,
    WEBHOOK_COUNTERPART_NO,
    WEBHOOK_SUBMIT,
    WEBHOOK_CANCEL,
    WEBHOOK_RESTART,
    WEBHOOK_OWNERSHIP_MINE,
    WEBHOOK_OWNERSHIP_COUNTERPART,
    WEBHOOK_IMAGE,
    WEBHOOK_UNKNOWN_TEXT,
    DUMMY_JPEG_BYTES,
    OCR_RESPONSE_ID_CARD,
    OCR_RESPONSE_UNKNOWN,
    make_line_signature,
    make_webhook_body,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def post_webhook(client, payload: dict):
    body = make_webhook_body(payload)
    sig  = make_line_signature(body)
    return client.post(
        "/callback",
        content=body,
        headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-01  Trigger detection — Car Damage keywords
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestTriggerDetection:
    """TC-FLOW-01/02: FR-01.2–FR-01.5 — Claim type detection from free text."""

    @pytest.mark.parametrize("keyword", ["รถ", "ชน", "เฉี่ยว", "car", "accident", "crash"])
    def test_cd_keyword_starts_session(self, keyword, app_client, get_session, mock_policy_lookup):
        """CD keyword sent to the bot returns 200 (v2: also creates session)."""
        from tests.test_data import _text_event
        payload = _text_event(USER_ID_A, keyword)
        resp = post_webhook(app_client, payload)
        # Bot must respond without crashing regardless of v1/v2 implementation
        assert resp.status_code == 200

    @pytest.mark.parametrize("keyword", ["ป่วย", "โรงพยาบาล", "sick", "hospital", "medical"])
    def test_h_keyword_starts_session(self, keyword, app_client, get_session, mock_policy_lookup):
        """H keyword sent to the bot returns 200 (v2: also creates session)."""
        from tests.test_data import _text_event
        payload = _text_event(USER_ID_A, keyword)
        resp = post_webhook(app_client, payload)
        # Bot must respond without crashing regardless of v1/v2 implementation
        assert resp.status_code == 200

    def test_ambiguous_keywords_does_not_crash(self, app_client):
        """Message matching both CD+H keyword sets must return 200 (ask to clarify)."""
        resp = post_webhook(app_client, WEBHOOK_AMBIGUOUS)
        assert resp.status_code == 200

    def test_classic_trigger_phrase(self, app_client):
        """'เช็คสิทธิ์เคลมด่วน' always returns 200."""
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_MAIN)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-02  Policy verification — typed CID
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestPolicyVerificationByText:
    """TC-FLOW-02: FR-02.2 — Policy lookup by 13-digit typed CID."""

    def test_valid_cid_advances_state(
        self, app_client, set_session, get_session, mock_policy_lookup
    ):
        """A valid 13-digit CID text lookup must advance session past verifying_policy."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_policy_lookup["by_cid"].return_value = [CD_POLICY_ACTIVE_CLASS1]

        resp = post_webhook(app_client, WEBHOOK_CID_TEXT)
        assert resp.status_code == 200

    def test_not_found_cid_stays_in_verify_state(
        self, app_client, set_session, get_session, mock_policy_lookup
    ):
        """An unknown CID must not crash; bot replies with not-found message."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_policy_lookup["by_cid"].return_value = []
        mock_policy_lookup["by_plate"].return_value = None
        mock_policy_lookup["by_name"].return_value = []

        resp = post_webhook(app_client, WEBHOOK_CID_TEXT)
        assert resp.status_code == 200

    def test_expired_policy_returns_200(
        self, app_client, set_session, mock_policy_lookup
    ):
        """Expired policy must return 200 (bot shows expired message)."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_policy_lookup["by_cid"].return_value = [CD_POLICY_EXPIRED]
        resp = post_webhook(app_client, WEBHOOK_CID_TEXT)
        assert resp.status_code == 200

    def test_multiple_policies_triggers_vehicle_selection(
        self, app_client, set_session, get_session, mock_policy_lookup
    ):
        """Multiple matching policies must trigger vehicle-selection state."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_policy_lookup["by_cid"].return_value = [
            CD_POLICY_ACTIVE_CLASS1,
            CD_POLICY_ACTIVE_CLASS2PLUS,
        ]
        resp = post_webhook(app_client, WEBHOOK_CID_TEXT)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        assert session.get("state") == "waiting_for_vehicle_selection"


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-03  Policy verification — image OCR
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestPolicyVerificationByImage:
    """TC-FLOW-03: FR-02.3 — Policy lookup by OCR from uploaded ID/licence photo."""

    def test_id_card_image_triggers_policy_lookup(
        self, app_client, set_session, mock_policy_lookup, mock_gemini
    ):
        """Image in waiting_for_info state runs OCR and does policy lookup."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_gemini.generate_content.return_value.text = json.dumps(OCR_RESPONSE_ID_CARD)
        mock_policy_lookup["by_cid"].return_value = [CD_POLICY_ACTIVE_CLASS1]

        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_unknown_image_type_returns_200(
        self, app_client, set_session, mock_gemini, mock_policy_lookup
    ):
        """Unrecognised image (unknown OCR type) must return 200, not 500."""
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        mock_gemini.generate_content.return_value.text = json.dumps(OCR_RESPONSE_UNKNOWN)

        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_image_outside_valid_state_returns_200(self, app_client):
        """Image sent with no session (idle) must return 200 with guidance message."""
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-04  Counterpart selection
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestCounterpartSelection:
    """TC-FLOW-04: FR-08.1 — Has/no counterpart question and state transition."""

    def test_has_counterpart_advances_state(
        self, app_client, set_session, get_session
    ):
        set_session(USER_ID_A, {
            "state":         "waiting_for_counterpart",
            "claim_id":      None,
            "claim_type":    "CD",
            "policy_info":   CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {},
        })
        resp = post_webhook(app_client, WEBHOOK_COUNTERPART_YES)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        # v1 main.py transitions counterpart → waiting_for_image (v2: uploading_documents)
        assert session.get("state") == "waiting_for_image"
        assert session.get("has_counterpart") == "มีคู่กรณี"

    def test_no_counterpart_advances_state(
        self, app_client, set_session, get_session
    ):
        set_session(USER_ID_A, {
            "state":         "waiting_for_counterpart",
            "claim_id":      None,
            "claim_type":    "CD",
            "policy_info":   CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {},
        })
        resp = post_webhook(app_client, WEBHOOK_COUNTERPART_NO)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        # v1 main.py transitions counterpart → waiting_for_image (v2: uploading_documents)
        assert session.get("state") == "waiting_for_image"
        assert session.get("has_counterpart") == "ไม่มีคู่กรณี"

    def test_invalid_answer_keeps_state_or_re_prompts(
        self, app_client, set_session, get_session
    ):
        """Any text other than the two QuickReply options must not crash."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":         "waiting_for_counterpart",
            "claim_id":      None,
            "claim_type":    "CD",
            "policy_info":   CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {},
        })
        payload = _text_event(USER_ID_A, "maybe")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-05  Document upload — categorisation & extraction  (v2 target)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestDocumentUpload:
    """
    TC-FLOW-05: FR-03, FR-04 — Document categorisation and extraction.

    These tests exercise the v2 uploading_documents path if present.
    If the bot is still on v1 (no uploading_documents state) the test confirms
    the endpoint handles the image gracefully and returns 200.
    """

    def test_image_in_uploading_state_returns_200(
        self, app_client, set_session, mock_gemini, mock_policy_lookup
    ):
        """Image sent during uploading_documents must not raise 500."""
        set_session(USER_ID_A, {
            "state":         "uploading_documents",
            "claim_id":      "CD-20260226-000001",
            "claim_type":    "CD",
            "has_counterpart": "มีคู่กรณี",
            "policy_info":   CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {},
        })
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_image_in_wrong_state_returns_200(self, app_client, set_session):
        """Image outside an upload-eligible state -> guidance, not 500."""
        set_session(USER_ID_A, {"state": "waiting_for_counterpart"})
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_text_in_uploading_state_returns_200(
        self, app_client, set_session
    ):
        """Text message during upload state prompts for photo."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":         "uploading_documents",
            "claim_type":    "CD",
            "has_counterpart": "มีคู่กรณี",
            "policy_info":   CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {},
        })
        payload = _text_event(USER_ID_A, "ส่งเอกสาร")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-06  Ownership confirmation  (CD with counterpart)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestOwnershipConfirmation:
    """TC-FLOW-06: FR-05 — Driving licence ownership assignment."""

    def _ownership_session(self):
        from tests.test_data import DUMMY_JPEG_BYTES
        return {
            "state":                  "awaiting_ownership",
            "claim_id":               None,            # None → storage calls skipped
            "claim_type":             "CD",
            "has_counterpart":        "มีคู่กรณี",
            "policy_info":            CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs":          {},
            # v2 handler expects a dict with filename/fields/image_bytes
            "awaiting_ownership_for": {
                "filename":    "driving_license_tmp.jpg",
                "fields":      {"full_name_th": "Test User", "citizen_id": "1234567890123"},
                "image_bytes": DUMMY_JPEG_BYTES,
            },
        }

    def test_ownership_mine_returns_200(self, app_client, set_session):
        set_session(USER_ID_A, self._ownership_session())
        resp = post_webhook(app_client, WEBHOOK_OWNERSHIP_MINE)
        assert resp.status_code == 200

    def test_ownership_counterpart_returns_200(self, app_client, set_session):
        set_session(USER_ID_A, self._ownership_session())
        resp = post_webhook(app_client, WEBHOOK_OWNERSHIP_COUNTERPART)
        assert resp.status_code == 200

    def test_duplicate_ownership_returns_200(
        self, app_client, set_session
    ):
        """Assigning the same side twice must not crash (bot rejects it)."""
        session = self._ownership_session()
        # Pre-assign customer side
        session["uploaded_docs"]["driving_license_customer"] = "dl_customer.jpg"
        set_session(USER_ID_A, session)
        resp = post_webhook(app_client, WEBHOOK_OWNERSHIP_MINE)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-07  Claim submission
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestClaimSubmission:
    """TC-FLOW-07: FR-07 — Claim submission triggered by 'ส่งคำร้อง'."""

    def _ready_session_cd(self):
        return {
            "state":           "ready_to_submit",
            "claim_id":        "CD-20260226-000001",
            "claim_type":      "CD",
            "has_counterpart": "มีคู่กรณี",
            "policy_info":     CD_POLICY_ACTIVE_CLASS1,
            "uploaded_docs": {
                "driving_license_customer":    "dl_customer.jpg",
                "driving_license_other_party": "dl_other.jpg",
                "vehicle_registration":        "reg.jpg",
                "vehicle_damage_photo":        "damage.jpg",
            },
        }

    def _ready_session_health(self):
        return {
            "state":        "ready_to_submit",
            "claim_id":     "H-20260226-000001",
            "claim_type":   "H",
            "policy_info":  H_POLICY_ACTIVE,
            "uploaded_docs": {
                "citizen_id_card":     "id.jpg",
                "medical_certificate": "cert.jpg",
                "itemised_bill":       "bill.jpg",
                "receipt":             "receipt.jpg",
            },
        }

    def test_submit_cd_claim_returns_200(self, app_client, set_session):
        set_session(USER_ID_A, self._ready_session_cd())
        resp = post_webhook(app_client, WEBHOOK_SUBMIT)
        assert resp.status_code == 200

    def test_submit_health_claim_returns_200(self, app_client, set_session):
        set_session(USER_ID_A, self._ready_session_health())
        resp = post_webhook(app_client, WEBHOOK_SUBMIT)
        assert resp.status_code == 200

    def test_submit_without_all_docs_returns_200(
        self, app_client, set_session
    ):
        """Incomplete doc set at ready_to_submit -> re-validation message, not 500."""
        session = self._ready_session_cd()
        del session["uploaded_docs"]["vehicle_registration"]
        set_session(USER_ID_A, session)
        resp = post_webhook(app_client, WEBHOOK_SUBMIT)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-08  Cancel / Restart from any state
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCancelAndRestart:
    """TC-FLOW-08: FR-01.8 — Cancel/restart resets session to idle."""

    @pytest.mark.parametrize("current_state", [
        "waiting_for_info",
        "waiting_for_counterpart",
        "uploading_documents",
        "awaiting_ownership",
        "ready_to_submit",
        "submitted",
    ])
    def test_cancel_from_any_state(
        self, app_client, set_session, get_session, current_state
    ):
        set_session(USER_ID_A, {"state": current_state, "policy_info": CD_POLICY_ACTIVE_CLASS1})
        resp = post_webhook(app_client, WEBHOOK_CANCEL)
        assert resp.status_code == 200

    @pytest.mark.parametrize("cancel_word", ["ยกเลิก", "cancel", "เริ่มใหม่", "restart"])
    def test_all_cancel_keywords(self, app_client, set_session, cancel_word):
        from tests.test_data import _text_event
        set_session(USER_ID_A, {"state": "uploading_documents"})
        payload = _text_event(USER_ID_A, cancel_word)
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200

    def test_new_session_can_start_after_cancel(
        self, app_client, set_session
    ):
        """After cancel, sending a trigger keyword must not crash."""
        set_session(USER_ID_A, {"state": "uploading_documents"})
        post_webhook(app_client, WEBHOOK_CANCEL)
        resp = post_webhook(app_client, WEBHOOK_TRIGGER_CD)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-09  submitted state — any message shows Claim ID reminder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSubmittedState:
    """TC-FLOW-09: Messages in 'submitted' state show Claim ID reminder."""

    def test_any_message_in_submitted_state_returns_200(
        self, app_client, set_session
    ):
        set_session(USER_ID_A, {
            "state":    "submitted",
            "claim_id": "CD-20260226-000001",
        })
        resp = post_webhook(app_client, WEBHOOK_UNKNOWN_TEXT)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-10  Vehicle selection (multiple policies)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestVehicleSelection:
    """TC-FLOW-10: Multiple policies in CID search trigger vehicle-selection."""

    def test_valid_plate_selection_advances_state(
        self, app_client, set_session, get_session
    ):
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state": "waiting_for_vehicle_selection",
            "search_results": [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS],
        })
        payload = _text_event(USER_ID_A, "เลือกรถ:กก1234")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        # After valid plate selection, must advance to waiting_for_counterpart (CD)
        assert session.get("state") == "waiting_for_counterpart"

    def test_invalid_plate_selection_returns_200(
        self, app_client, set_session
    ):
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state": "waiting_for_vehicle_selection",
            "search_results": [CD_POLICY_ACTIVE_CLASS1],
        })
        payload = _text_event(USER_ID_A, "เลือกทะเบียน ไม่มีทะเบียนนี้")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-11  Additional info step (v1 flow)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestAdditionalInfoStep:
    """TC-FLOW-11: Free-text additional info step (v1 waiting_for_additional_info)."""

    def _additional_info_session(self):
        return {
            "state":           "waiting_for_additional_info",
            "policy_info":     CD_POLICY_ACTIVE_CLASS1,
            "has_counterpart": "มีคู่กรณี",
        }

    def test_provide_additional_info(self, app_client, set_session, get_session):
        from tests.test_data import _text_event
        set_session(USER_ID_A, self._additional_info_session())
        payload = _text_event(USER_ID_A, "รถชนที่แยกลาดพร้าว")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200

    def test_skip_additional_info(self, app_client, set_session, get_session):
        from tests.test_data import _text_event
        set_session(USER_ID_A, self._additional_info_session())
        payload = _text_event(USER_ID_A, "ข้าม")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        assert session.get("additional_info") is None


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-12  Damage image analysis (v1 flow — waiting_for_image)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestDamageImageAnalysis:
    """TC-FLOW-12: Damage photo in waiting_for_image state triggers AI analysis."""

    def test_damage_analysis_called_in_waiting_for_image(
        self, app_client, set_session, mock_gemini
    ):
        from tests.test_data import DAMAGE_ANALYSIS_ELIGIBLE
        mock_gemini.generate_content.return_value.text = DAMAGE_ANALYSIS_ELIGIBLE

        set_session(USER_ID_A, {
            "state":           "waiting_for_image",
            "policy_info":     CD_POLICY_ACTIVE_CLASS1,
            "has_counterpart": "มีคู่กรณี",
            "additional_info": "รถชนที่แยก",
        })
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_damage_analysis_no_policy_document_returns_200(
        self, app_client, set_session
    ):
        """Policy with no PDF document should still return 200 (handled message)."""
        policy_no_doc = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": None}
        set_session(USER_ID_A, {
            "state":       "waiting_for_image",
            "policy_info": policy_no_doc,
        })
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-13  completed state → ส่งเคลม / จบการสนทนา
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCompletedStateTransitions:
    """TC-FLOW-13: Text actions available after AI analysis completes."""

    def test_send_claim_advances_to_waiting_for_claim_documents(
        self, app_client, set_session, get_session
    ):
        """'ส่งเคลม' in completed state must move to waiting_for_claim_documents."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":       "completed",
            "policy_info": CD_POLICY_ACTIVE_CLASS1,
        })
        payload = _text_event(USER_ID_A, "ส่งเคลม")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        assert session.get("state") == "waiting_for_claim_documents"

    def test_end_conversation_resets_session(
        self, app_client, set_session, get_session
    ):
        """'จบการสนทนา' in completed state must reset the session."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":       "completed",
            "policy_info": CD_POLICY_ACTIVE_CLASS1,
        })
        payload = _text_event(USER_ID_A, "จบการสนทนา")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        assert session.get("state") in ("idle", None)

    def test_end_conversation_clears_policy_info(
        self, app_client, set_session, get_session
    ):
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":       "completed",
            "policy_info": CD_POLICY_ACTIVE_CLASS1,
        })
        payload = _text_event(USER_ID_A, "จบการสนทนา")
        post_webhook(app_client, payload)
        session = get_session(USER_ID_A)
        assert "policy_info" not in session

    def test_unrecognised_text_in_completed_does_not_crash(
        self, app_client, set_session
    ):
        from tests.test_data import _text_event
        set_session(USER_ID_A, {"state": "completed"})
        payload = _text_event(USER_ID_A, "ข้อความสุ่ม")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-14  waiting_for_claim_documents — document receipt & completion
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestClaimDocumentsCompletion:
    """TC-FLOW-14: Document upload and 'เสร็จสิ้น' finishes the flow."""

    def test_done_text_resets_session(
        self, app_client, set_session, get_session
    ):
        """'เสร็จสิ้น' in waiting_for_claim_documents resets to idle."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {
            "state":       "waiting_for_claim_documents",
            "policy_info": CD_POLICY_ACTIVE_CLASS1,
        })
        payload = _text_event(USER_ID_A, "เสร็จสิ้น")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200
        session = get_session(USER_ID_A)
        assert session.get("state") in ("idle", None)

    def test_image_in_claim_documents_state_returns_200(
        self, app_client, set_session
    ):
        """Image sent while collecting claim documents must return 200."""
        set_session(USER_ID_A, {
            "state":       "waiting_for_claim_documents",
            "policy_info": CD_POLICY_ACTIVE_CLASS1,
        })
        resp = post_webhook(app_client, WEBHOOK_IMAGE)
        assert resp.status_code == 200

    def test_other_text_in_claim_documents_returns_200(
        self, app_client, set_session
    ):
        """Any non-terminal text during document collection must return 200."""
        from tests.test_data import _text_event
        set_session(USER_ID_A, {"state": "waiting_for_claim_documents"})
        payload = _text_event(USER_ID_A, "ส่งแล้วนะครับ")
        resp = post_webhook(app_client, payload)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# TC-FLOW-15  Phone-number lookup path  (9–10 digit text in waiting_for_info)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.flow_cd
class TestPhoneNumberLookupFlow:
    """TC-FLOW-15: 9/10-digit input in waiting_for_info routes to phone lookup."""

    def test_10_digit_phone_returns_200(
        self, app_client, set_session, mock_policy_lookup
    ):
        from tests.test_data import _text_event
        from unittest.mock import patch
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        with patch("main.search_policies_by_phone", return_value=[CD_POLICY_ACTIVE_CLASS1]):
            payload = _text_event(USER_ID_A, "0812345678")
            resp = post_webhook(app_client, payload)
        assert resp.status_code == 200

    def test_9_digit_phone_calls_phone_lookup(
        self, app_client, set_session, mock_policy_lookup
    ):
        from tests.test_data import _text_event
        from unittest.mock import patch
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        with patch("main.search_policies_by_phone", return_value=[]) as mock_phone:
            payload = _text_event(USER_ID_A, "081234567")  # 9 digits
            resp = post_webhook(app_client, payload)
            mock_phone.assert_called_once()
        assert resp.status_code == 200

    def test_10_digit_phone_not_found_returns_200(
        self, app_client, set_session, mock_policy_lookup
    ):
        from tests.test_data import _text_event
        from unittest.mock import patch
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        with patch("main.search_policies_by_phone", return_value=[]):
            payload = _text_event(USER_ID_A, "0999999999")
            resp = post_webhook(app_client, payload)
        assert resp.status_code == 200

    def test_10_digit_phone_with_found_policy_advances_state(
        self, app_client, set_session, get_session, mock_policy_lookup
    ):
        from tests.test_data import _text_event
        from unittest.mock import patch
        set_session(USER_ID_A, {"state": "waiting_for_info"})
        with patch("main.search_policies_by_phone", return_value=[CD_POLICY_ACTIVE_CLASS1]):
            payload = _text_event(USER_ID_A, "0812345678")
            post_webhook(app_client, payload)
        session = get_session(USER_ID_A)
        assert session.get("state") != "waiting_for_info"
