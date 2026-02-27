"""
test_handlers.py
================
Unit tests for all handler modules: trigger, identity, documents, submit.

Strategy
--------
- Call handler functions directly (no HTTP server).
- LINE API mocked with MagicMock.
- The v2 handlers import flex_messages functions that don't yet exist in
  flex_messages.py (Phase-2 additions not yet implemented). We inject stubs
  using setattr BEFORE any import of the handler modules, via the module-scoped
  ``inject_flex_stubs`` autouse fixture. This is the same technique used in
  conftest.py for genai.
- AI lazy imports (extract_id_from_image, categorise_document, extract_fields)
  are patched at their source module with ``patch("ai.ocr.extract_id_from_image")``.
- Storage functions patched so no real file-system writes happen.
- Policy lookup functions patched on their binding inside each handler module.

Areas covered
-------------
  HND-01  handlers/trigger.py    — _detect_claim_type, is_trigger, handle_trigger,
                                   handle_claim_type_selection, _start_claim
  HND-02  handlers/identity.py   — handle_policy_text, handle_policy_image,
                                   handle_vehicle_selection, _process_search_result,
                                   _apply_single_policy
  HND-03  handlers/documents.py  — handle_counterpart_answer, handle_ownership_answer,
                                   handle_document_image, _required_doc_keys, _missing_docs
  HND-04  handlers/submit.py     — handle_submit_request, _generate_summary
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import io

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Module-level fixture: inject missing flex_messages stubs
# ─────────────────────────────────────────────────────────────────────────────

from linebot.v3.messaging import FlexContainer

_DUMMY_FLEX = FlexContainer.from_dict({
    "type": "bubble",
    "body": {"type": "box", "layout": "vertical", "contents": []}
})

_MISSING_FLEX_NAMES = [
    "create_claim_confirmed_flex",
    "create_claim_type_selector_flex",
    "create_document_checklist_flex",
    "create_doc_received_flex",
    "create_submit_prompt_flex",
    "create_ownership_question_flex",
    "create_submission_confirmed_flex",
    "create_health_policy_info_flex",
]


@pytest.fixture(autouse=True, scope="module")
def inject_flex_stubs():
    """Inject missing flex_messages functions as stubs returning a valid FlexContainer."""
    import flex_messages as fm
    _saved = {}
    for name in _MISSING_FLEX_NAMES:
        if not hasattr(fm, name):
            _saved[name] = None
            setattr(fm, name, MagicMock(return_value=_DUMMY_FLEX))
    yield
    # Restore state (remove injected stubs, leave pre-existing untouched)
    for name, original in _saved.items():
        if original is None:
            try:
                delattr(fm, name)
            except AttributeError:
                pass
        else:
            setattr(fm, name, original)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_api():
    api = MagicMock()
    api.reply_message = MagicMock()
    api.push_message = MagicMock()
    return api


def _make_event(user_id: str = "Utest0001", reply_token: str = "rt-001"):
    event = MagicMock()
    event.source.user_id = user_id
    event.reply_token = reply_token
    return event


def _make_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="JPEG")
    return buf.getvalue()


_UID = "Utest0001"
_CLAIM_ID_CD = "CD-20260226-000001"
_CLAIM_ID_H  = "H-20260226-000001"

_ACTIVE_CD_POLICY = {
    "first_name": "Somchai",
    "last_name": "Test",
    "plate": "กข1234",
    "vehicle_plate": "กข1234",
    "car_model": "Honda Civic",
    "insurance_type": "ชั้น 1",
    "insurance_company": "TestIns",
    "status": "active",
    "policy_number": "POL-001",
    "coverage_class": "1",
}
_ACTIVE_H_POLICY = {
    "first_name": "Somchai",
    "last_name": "Test",
    "plan": "Basic Health",
    "status": "active",
    "policy_number": "HPOL-001",
}
_EXPIRED_POLICY = {
    "plate": "บบ9999",
    "insurance_company": "OldIns",
    "status": "expired",
    "policy_number": "POL-EXP",
}


# ─────────────────────────────────────────────────────────────────────────────
# HND-01  handlers/trigger.py
# ─────────────────────────────────────────────────────────────────────────────

class TestTriggerHandler:
    """HND-01: trigger detection and claim session initialisation."""

    # ── _detect_claim_type ───────────────────────────────────────────────────

    def test_detect_cd_keyword_returns_cd(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("รถชนกัน") == "CD"

    def test_detect_h_keyword_returns_h(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("ป่วยไข้") == "H"

    def test_detect_both_keywords_returns_ambiguous(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("รถชน ป่วย") == "ambiguous"

    def test_detect_no_keywords_returns_none(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("สวัสดีครับ") == "none"

    def test_detect_english_car_keyword(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("car accident") == "CD"

    def test_detect_english_health_keyword(self):
        from handlers.trigger import _detect_claim_type
        assert _detect_claim_type("hospital visit") == "H"

    # ── is_trigger ───────────────────────────────────────────────────────────

    def test_is_trigger_with_main_trigger_keyword(self):
        from handlers.trigger import is_trigger
        assert is_trigger("เคลม") is True

    def test_is_trigger_with_cd_keywords(self):
        from handlers.trigger import is_trigger
        assert is_trigger("รถชน") is True

    def test_is_trigger_with_h_keywords(self):
        from handlers.trigger import is_trigger
        assert is_trigger("ป่วย") is True

    def test_is_trigger_with_unknown_text_returns_false(self):
        from handlers.trigger import is_trigger
        assert is_trigger("สวัสดีครับ") is False

    # ── handle_trigger — CD ──────────────────────────────────────────────────

    @patch("handlers.trigger.create_claim")
    @patch("handlers.trigger.next_claim_id", return_value=_CLAIM_ID_CD)
    def test_handle_trigger_cd_sends_reply(self, _next, _create):
        from handlers.trigger import handle_trigger
        api = _make_api()
        sessions = {_UID: {"state": "idle"}}
        handle_trigger(api, _make_event(_UID), _UID, sessions, "รถชน")
        api.reply_message.assert_called_once()

    @patch("handlers.trigger.create_claim")
    @patch("handlers.trigger.next_claim_id", return_value=_CLAIM_ID_CD)
    def test_handle_trigger_cd_sets_verifying_policy_state(self, _next, _create):
        from handlers.trigger import handle_trigger
        sessions = {_UID: {"state": "idle"}}
        handle_trigger(_make_api(), _make_event(_UID), _UID, sessions, "รถชน")
        assert sessions[_UID]["state"] == "verifying_policy"

    @patch("handlers.trigger.create_claim")
    @patch("handlers.trigger.next_claim_id", return_value=_CLAIM_ID_CD)
    def test_handle_trigger_cd_stores_claim_id(self, _next, _create):
        from handlers.trigger import handle_trigger
        sessions = {_UID: {"state": "idle"}}
        handle_trigger(_make_api(), _make_event(_UID), _UID, sessions, "รถชน")
        assert sessions[_UID]["claim_id"] == _CLAIM_ID_CD

    # ── handle_trigger — ambiguous ───────────────────────────────────────────

    def test_handle_trigger_ambiguous_shows_type_selector(self):
        from handlers.trigger import handle_trigger
        api = _make_api()
        sessions = {_UID: {"state": "idle"}}
        handle_trigger(api, _make_event(_UID), _UID, sessions, "รถชน ป่วย")
        assert sessions[_UID]["state"] == "detecting_claim_type"
        api.reply_message.assert_called_once()

    # ── handle_claim_type_selection ──────────────────────────────────────────

    @patch("handlers.trigger.create_claim")
    @patch("handlers.trigger.next_claim_id", return_value=_CLAIM_ID_CD)
    def test_handle_claim_type_selection_cd(self, _next, _create):
        from handlers.trigger import handle_claim_type_selection
        sessions = {_UID: {"state": "detecting_claim_type"}}
        handle_claim_type_selection(_make_api(), _make_event(_UID), _UID, sessions, "CD")
        assert sessions[_UID]["claim_type"] == "CD"

    @patch("handlers.trigger.create_claim")
    @patch("handlers.trigger.next_claim_id", return_value=_CLAIM_ID_H)
    def test_handle_claim_type_selection_h(self, _next, _create):
        from handlers.trigger import handle_claim_type_selection
        sessions = {_UID: {"state": "detecting_claim_type"}}
        handle_claim_type_selection(_make_api(), _make_event(_UID), _UID, sessions, "H")
        assert sessions[_UID]["claim_type"] == "H"

    def test_handle_claim_type_selection_invalid_shows_selector(self):
        from handlers.trigger import handle_claim_type_selection
        api = _make_api()
        sessions = {_UID: {"state": "detecting_claim_type"}}
        handle_claim_type_selection(api, _make_event(_UID), _UID, sessions, "อื่นๆ")
        api.reply_message.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# HND-02  handlers/identity.py
# ─────────────────────────────────────────────────────────────────────────────

class TestIdentityHandler:
    """HND-02: policy verification via text, image, and vehicle selection."""

    def _base_session(self, claim_type="CD"):
        return {
            _UID: {
                "state": "verifying_policy",
                "claim_id": _CLAIM_ID_CD,
                "claim_type": claim_type,
                "search_results": [],
            }
        }

    # ── handle_policy_text ───────────────────────────────────────────────────

    def test_handle_policy_text_cid_found_calls_reply(self):
        with patch("handlers.identity.search_policies_by_cid", return_value=[_ACTIVE_CD_POLICY]), \
             patch("handlers.identity.update_claim_status"):
            from handlers.identity import handle_policy_text
            api = _make_api()
            sessions = self._base_session()
            handle_policy_text(api, _make_event(_UID), _UID, sessions, "7564985348794")
        api.reply_message.assert_called_once()

    def test_handle_policy_text_cid_not_found_sends_reply(self):
        with patch("handlers.identity.search_policies_by_cid", return_value=[]):
            from handlers.identity import handle_policy_text
            api = _make_api()
            sessions = self._base_session()
            handle_policy_text(api, _make_event(_UID), _UID, sessions, "0000000000000")
        api.reply_message.assert_called_once()

    def test_handle_policy_text_multiple_results_shows_vehicle_selector(self):
        two_policies = [_ACTIVE_CD_POLICY, {**_ACTIVE_CD_POLICY, "plate": "คง5678", "vehicle_plate": "คง5678"}]
        with patch("handlers.identity.search_policies_by_cid", return_value=two_policies):
            from handlers.identity import handle_policy_text
            api = _make_api()
            sessions = self._base_session()
            handle_policy_text(api, _make_event(_UID), _UID, sessions, "7564985348794")
        assert sessions[_UID]["state"] == "waiting_for_vehicle_selection"

    def test_handle_policy_text_expired_policy_sends_expired_message(self):
        with patch("handlers.identity.search_policies_by_cid", return_value=[_EXPIRED_POLICY]):
            from handlers.identity import handle_policy_text
            api = _make_api()
            sessions = self._base_session()
            handle_policy_text(api, _make_event(_UID), _UID, sessions, "7564985348794")
        api.reply_message.assert_called_once()

    def test_handle_policy_text_health_cid_found(self):
        with patch("handlers.identity.search_health_policies_by_cid", return_value=[_ACTIVE_H_POLICY]), \
             patch("handlers.identity.update_claim_status"):
            from handlers.identity import handle_policy_text
            api = _make_api()
            sessions = self._base_session(claim_type="H")
            handle_policy_text(api, _make_event(_UID), _UID, sessions, "8901234567890")
        api.reply_message.assert_called_once()

    # ── handle_policy_image ──────────────────────────────────────────────────

    def test_handle_policy_image_id_card_found_uses_push(self):
        ocr_result = {"type": "id_card", "value": "7564985348794"}
        with patch("ai.ocr.extract_id_from_image", return_value=ocr_result), \
             patch("handlers.identity.search_policies_by_cid", return_value=[_ACTIVE_CD_POLICY]), \
             patch("handlers.identity.update_claim_status"):
            from handlers.identity import handle_policy_image
            api = _make_api()
            sessions = self._base_session()
            handle_policy_image(api, _UID, sessions, b"fake_image")
        api.push_message.assert_called_once()

    def test_handle_policy_image_unknown_sends_failure_push(self):
        ocr_result = {"type": "unknown", "value": None}
        with patch("ai.ocr.extract_id_from_image", return_value=ocr_result):
            from handlers.identity import handle_policy_image
            api = _make_api()
            sessions = self._base_session()
            handle_policy_image(api, _UID, sessions, b"fake_image")
        api.push_message.assert_called_once()
        api.reply_message.assert_not_called()

    def test_handle_policy_image_license_plate_searches_by_plate(self):
        ocr_result = {"type": "license_plate", "value": "กข1234"}
        with patch("ai.ocr.extract_id_from_image", return_value=ocr_result), \
             patch("handlers.identity.search_policies_by_plate", return_value=_ACTIVE_CD_POLICY), \
             patch("handlers.identity.update_claim_status"):
            from handlers.identity import handle_policy_image
            api = _make_api()
            sessions = self._base_session()
            handle_policy_image(api, _UID, sessions, b"fake_image")
        api.push_message.assert_called_once()

    # ── handle_vehicle_selection ─────────────────────────────────────────────

    def test_handle_vehicle_selection_valid_plate_advances_state(self):
        sessions = {
            _UID: {
                "state": "waiting_for_vehicle_selection",
                "claim_id": _CLAIM_ID_CD,
                "claim_type": "CD",
                "search_results": [_ACTIVE_CD_POLICY],
            }
        }
        with patch("handlers.identity.update_claim_status"):
            from handlers.identity import handle_vehicle_selection
            api = _make_api()
            handle_vehicle_selection(api, _make_event(_UID), _UID, sessions, "เลือกทะเบียน กข1234")
        # CD → waiting_for_counterpart
        assert sessions[_UID]["state"] == "waiting_for_counterpart"

    def test_handle_vehicle_selection_invalid_plate_sends_error(self):
        sessions = {
            _UID: {
                "state": "waiting_for_vehicle_selection",
                "claim_id": _CLAIM_ID_CD,
                "claim_type": "CD",
                "search_results": [_ACTIVE_CD_POLICY],
            }
        }
        from handlers.identity import handle_vehicle_selection
        api = _make_api()
        handle_vehicle_selection(api, _make_event(_UID), _UID, sessions, "เลือกทะเบียน ไม่มีป้าย9999")
        api.reply_message.assert_called_once()
        assert sessions[_UID]["state"] == "waiting_for_vehicle_selection"


# ─────────────────────────────────────────────────────────────────────────────
# HND-03  handlers/documents.py
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentsHandler:
    """HND-03: document upload, counterpart, ownership, and required-docs helpers."""

    def _base_cd_session(self, has_counterpart="ไม่มีคู่กรณี"):
        return {
            _UID: {
                "state": "uploading_documents",
                "claim_id": None,
                "claim_type": "CD",
                "has_counterpart": has_counterpart,
                "uploaded_docs": {},
                "awaiting_ownership_for": None,
            }
        }

    # ── handle_counterpart_answer ────────────────────────────────────────────

    def test_handle_counterpart_answer_yes_transitions_to_uploading(self):
        from handlers.documents import handle_counterpart_answer
        sessions = {
            _UID: {"state": "waiting_for_counterpart", "claim_id": None, "uploaded_docs": {}}
        }
        api = _make_api()
        handle_counterpart_answer(api, _make_event(_UID), _UID, sessions, "มีคู่กรณี")
        assert sessions[_UID]["state"] == "uploading_documents"
        assert sessions[_UID]["has_counterpart"] == "มีคู่กรณี"
        api.reply_message.assert_called_once()

    def test_handle_counterpart_answer_no_transitions_to_uploading(self):
        from handlers.documents import handle_counterpart_answer
        sessions = {
            _UID: {"state": "waiting_for_counterpart", "claim_id": None, "uploaded_docs": {}}
        }
        api = _make_api()
        handle_counterpart_answer(api, _make_event(_UID), _UID, sessions, "ไม่มีคู่กรณี")
        assert sessions[_UID]["state"] == "uploading_documents"

    def test_handle_counterpart_answer_invalid_text_re_prompts(self):
        from handlers.documents import handle_counterpart_answer
        sessions = {
            _UID: {"state": "waiting_for_counterpart", "claim_id": None, "uploaded_docs": {}}
        }
        api = _make_api()
        handle_counterpart_answer(api, _make_event(_UID), _UID, sessions, "maybe")
        api.reply_message.assert_called_once()
        assert sessions[_UID]["state"] == "waiting_for_counterpart"

    # ── handle_ownership_answer ──────────────────────────────────────────────

    def test_handle_ownership_answer_mine_sets_customer_key(self):
        sessions = self._base_cd_session(has_counterpart="มีคู่กรณี")
        sessions[_UID]["awaiting_ownership_for"] = {
            "filename": "driving_license_pending.jpg",
            "fields": {"full_name_th": "สมชาย"},
            "image_bytes": b"imgbytes",
        }
        from handlers.documents import handle_ownership_answer
        handle_ownership_answer(_make_api(), _make_event(_UID), _UID, sessions, "ของฉัน (ฝ่ายเรา)")
        assert "driving_license_customer" in sessions[_UID]["uploaded_docs"]

    def test_handle_ownership_answer_counterpart_sets_other_party_key(self):
        sessions = self._base_cd_session(has_counterpart="มีคู่กรณี")
        sessions[_UID]["awaiting_ownership_for"] = {
            "filename": "driving_license_pending.jpg",
            "fields": {},
            "image_bytes": b"imgbytes",
        }
        from handlers.documents import handle_ownership_answer
        handle_ownership_answer(_make_api(), _make_event(_UID), _UID, sessions, "คู่กรณี (อีกฝ่าย)")
        assert "driving_license_other_party" in sessions[_UID]["uploaded_docs"]

    def test_handle_ownership_answer_invalid_re_prompts(self):
        sessions = self._base_cd_session(has_counterpart="มีคู่กรณี")
        from handlers.documents import handle_ownership_answer
        api = _make_api()
        handle_ownership_answer(api, _make_event(_UID), _UID, sessions, "ไม่ทราบ")
        api.reply_message.assert_called_once()

    def test_handle_ownership_answer_duplicate_slot_re_prompts(self):
        sessions = self._base_cd_session(has_counterpart="มีคู่กรณี")
        sessions[_UID]["uploaded_docs"]["driving_license_customer"] = "already.jpg"
        sessions[_UID]["awaiting_ownership_for"] = {
            "filename": "new.jpg", "fields": {}, "image_bytes": b""
        }
        from handlers.documents import handle_ownership_answer
        api = _make_api()
        handle_ownership_answer(api, _make_event(_UID), _UID, sessions, "ของฉัน (ฝ่ายเรา)")
        api.reply_message.assert_called_once()

    # ── handle_document_image ────────────────────────────────────────────────

    def test_handle_document_image_valid_category_saved_in_session(self):
        sessions = self._base_cd_session()
        with patch("ai.categorise.categorise_document", return_value="vehicle_registration"), \
             patch("ai.extract.extract_fields", return_value={"plate": "กข1234"}):
            from handlers.documents import handle_document_image
            handle_document_image(_make_api(), _UID, sessions, _make_jpeg())
        assert "vehicle_registration" in sessions[_UID]["uploaded_docs"]

    def test_handle_document_image_unknown_category_pushes_rejection(self):
        sessions = self._base_cd_session()
        with patch("ai.categorise.categorise_document", return_value="unknown"):
            from handlers.documents import handle_document_image
            api = _make_api()
            handle_document_image(api, _UID, sessions, _make_jpeg())
        api.push_message.assert_called_once()
        assert not sessions[_UID]["uploaded_docs"]

    def test_handle_document_image_driving_license_with_counterpart_asks_ownership(self):
        sessions = self._base_cd_session(has_counterpart="มีคู่กรณี")
        with patch("ai.categorise.categorise_document", return_value="driving_license"), \
             patch("ai.extract.extract_fields", return_value={"full_name_th": "สมชาย"}):
            from handlers.documents import handle_document_image
            handle_document_image(_make_api(), _UID, sessions, _make_jpeg())
        assert sessions[_UID]["state"] == "awaiting_ownership"
        assert sessions[_UID]["awaiting_ownership_for"] is not None

    def test_handle_document_image_all_docs_complete_triggers_ready_state(self):
        sessions = self._base_cd_session()
        sessions[_UID]["uploaded_docs"] = {
            "driving_license_customer": "dl.jpg",
            "vehicle_damage_photo_1": "dmg.jpg",
        }
        with patch("ai.categorise.categorise_document", return_value="vehicle_registration"), \
             patch("ai.extract.extract_fields", return_value={"plate": "กข1234"}):
            from handlers.documents import handle_document_image
            handle_document_image(_make_api(), _UID, sessions, _make_jpeg())
        assert sessions[_UID]["state"] == "ready_to_submit"

    # ── _required_doc_keys ───────────────────────────────────────────────────

    def test_required_doc_keys_cd_no_counterpart(self):
        from handlers.documents import _required_doc_keys
        session = {"claim_type": "CD", "has_counterpart": "ไม่มีคู่กรณี"}
        keys = _required_doc_keys(session)
        assert "driving_license_customer" in keys
        assert "vehicle_registration" in keys
        assert "vehicle_damage_photo" in keys
        assert "driving_license_other_party" not in keys

    def test_required_doc_keys_cd_with_counterpart(self):
        from handlers.documents import _required_doc_keys
        session = {"claim_type": "CD", "has_counterpart": "มีคู่กรณี"}
        keys = _required_doc_keys(session)
        assert "driving_license_other_party" in keys

    def test_required_doc_keys_health(self):
        from handlers.documents import _required_doc_keys
        session = {"claim_type": "H", "has_counterpart": None}
        keys = _required_doc_keys(session)
        assert "citizen_id_card" in keys
        assert "medical_certificate" in keys
        assert "itemised_bill" in keys
        assert "receipt" in keys

    # ── _missing_docs ────────────────────────────────────────────────────────

    def test_missing_docs_nothing_uploaded_returns_all_required(self):
        from handlers.documents import _missing_docs
        session = {
            "claim_type": "CD",
            "has_counterpart": "ไม่มีคู่กรณี",
            "uploaded_docs": {},
        }
        assert len(_missing_docs(session)) > 0

    def test_missing_docs_all_uploaded_returns_empty(self):
        from handlers.documents import _missing_docs
        session = {
            "claim_type": "CD",
            "has_counterpart": "ไม่มีคู่กรณี",
            "uploaded_docs": {
                "driving_license_customer": "dl.jpg",
                "vehicle_registration": "reg.jpg",
                "vehicle_damage_photo_1": "dmg.jpg",
            },
        }
        assert _missing_docs(session) == []

    def test_missing_docs_partial_upload_returns_remaining(self):
        from handlers.documents import _missing_docs
        session = {
            "claim_type": "CD",
            "has_counterpart": "ไม่มีคู่กรณี",
            "uploaded_docs": {"driving_license_customer": "dl.jpg"},
        }
        missing = _missing_docs(session)
        assert "vehicle_registration" in missing
        assert "driving_license_customer" not in missing


# ─────────────────────────────────────────────────────────────────────────────
# HND-04  handlers/submit.py
# ─────────────────────────────────────────────────────────────────────────────

class TestSubmitHandler:
    """HND-04: claim submission and AI summary generation."""

    def _complete_cd_session(self):
        return {
            _UID: {
                "state": "ready_to_submit",
                "claim_id": _CLAIM_ID_CD,
                "claim_type": "CD",
                "has_counterpart": "ไม่มีคู่กรณี",
                "policy_info": _ACTIVE_CD_POLICY,
                "uploaded_docs": {
                    "driving_license_customer": "dl.jpg",
                    "vehicle_registration": "reg.jpg",
                    "vehicle_damage_photo_1": "dmg.jpg",
                },
                "additional_info": None,
            }
        }

    def _incomplete_cd_session(self):
        return {
            _UID: {
                "state": "ready_to_submit",
                "claim_id": _CLAIM_ID_CD,
                "claim_type": "CD",
                "has_counterpart": "ไม่มีคู่กรณี",
                "policy_info": _ACTIVE_CD_POLICY,
                "uploaded_docs": {"driving_license_customer": "dl.jpg"},
                "additional_info": None,
            }
        }

    # ── complete claim ────────────────────────────────────────────────────────

    def test_handle_submit_request_complete_sets_submitted_state(self):
        with patch("handlers.submit.claim_store.update_claim_status"), \
             patch("handlers.submit._generate_summary"):
            from handlers.submit import handle_submit_request
            sessions = self._complete_cd_session()
            handle_submit_request(_make_api(), _make_event(_UID), _UID, sessions)
        assert sessions[_UID]["state"] == "submitted"

    def test_handle_submit_request_complete_calls_update_status_submitted(self):
        with patch("handlers.submit.claim_store.update_claim_status") as mock_update, \
             patch("handlers.submit._generate_summary"):
            from handlers.submit import handle_submit_request
            sessions = self._complete_cd_session()
            handle_submit_request(_make_api(), _make_event(_UID), _UID, sessions)
        mock_update.assert_called_once()
        assert mock_update.call_args[1].get("status") == "Submitted"

    def test_handle_submit_request_complete_sends_reply(self):
        with patch("handlers.submit.claim_store.update_claim_status"), \
             patch("handlers.submit._generate_summary"):
            from handlers.submit import handle_submit_request
            sessions = self._complete_cd_session()
            api = _make_api()
            handle_submit_request(api, _make_event(_UID), _UID, sessions)
        api.reply_message.assert_called_once()

    # ── incomplete claim ─────────────────────────────────────────────────────

    def test_handle_submit_request_incomplete_does_not_call_update_status(self):
        with patch("handlers.submit.claim_store.update_claim_status") as mock_update:
            from handlers.submit import handle_submit_request
            sessions = self._incomplete_cd_session()
            handle_submit_request(_make_api(), _make_event(_UID), _UID, sessions)
        mock_update.assert_not_called()

    def test_handle_submit_request_incomplete_does_not_change_state(self):
        from handlers.submit import handle_submit_request
        sessions = self._incomplete_cd_session()
        handle_submit_request(_make_api(), _make_event(_UID), _UID, sessions)
        assert sessions[_UID]["state"] == "ready_to_submit"

    def test_handle_submit_request_incomplete_sends_reply_with_missing_list(self):
        from handlers.submit import handle_submit_request
        sessions = self._incomplete_cd_session()
        api = _make_api()
        handle_submit_request(api, _make_event(_UID), _UID, sessions)
        api.reply_message.assert_called_once()

    # ── _generate_summary ────────────────────────────────────────────────────

    def test_generate_summary_calls_call_gemini_and_saves(self):
        with patch("handlers.submit.claim_store.get_extracted_data", return_value={}), \
             patch("handlers.submit.claim_store.save_summary") as mock_save, \
             patch("ai.call_gemini", return_value="# Summary content") as mock_gemini:
            from handlers.submit import _generate_summary
            _generate_summary(_CLAIM_ID_CD, {
                "claim_type": "CD",
                "has_counterpart": "ไม่มีคู่กรณี",
                "policy_info": _ACTIVE_CD_POLICY,
            })
        mock_gemini.assert_called_once()
        mock_save.assert_called_once_with(_CLAIM_ID_CD, "# Summary content")

    def test_generate_summary_exception_does_not_raise(self):
        with patch("handlers.submit.claim_store.get_extracted_data", side_effect=Exception("db fail")):
            from handlers.submit import _generate_summary
            _generate_summary(_CLAIM_ID_CD, {"claim_type": "CD", "policy_info": {}})
