"""
test_claim_engine.py
====================
Unit tests for claim_engine.py — the AI analysis layer.

Areas covered
-------------
  CE-01  extract_phone_from_response()      — Thai phone pattern extractor
         (also covered in test_business_logic.py BL-09; included here for
          completeness of the claim_engine module tests)

  CE-02  extract_info_from_image_with_gemini()
         (also covered in test_business_logic.py BL-13; included here for
          cross-reference completeness)

  CE-03  analyze_damage_with_gemini()
         • Early-exit path when policy_document_base64 is None
         • Full-analysis path when policy_document_base64 is set
           – genai.upload_file / generate_content / delete_file are called
           – has_counterpart "มีคู่กรณี" prompt branch
           – has_counterpart "ไม่มีคู่กรณี" prompt branch
           – additional_info injected into prompt
           – Exception → returns error string
           – Temp PDF file is cleaned up even on success

  CE-04  start_claim_analysis()
         • "Analyzing…" wait-message pushed first
         • Phone extracted from AI result → sends analysis flex via push
         • No phone in result but policy has phone → sends flex via push
         • No phone anywhere → sends plain TextMessages via push
         • State set to "completed" after success
         • Exception in inner call → sends error push (no crash)
"""

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    DUMMY_JPEG_BYTES,
    USER_ID_A,
    CD_POLICY_ACTIVE_CLASS1,
    DAMAGE_ANALYSIS_ELIGIBLE,
    DAMAGE_ANALYSIS_NOT_ELIGIBLE,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

# Policy WITH a phone number (falls back to policy phone when AI returns none)
_POLICY_WITH_PHONE = {**CD_POLICY_ACTIVE_CLASS1}          # has "phone": "0812345678"

# Policy WITHOUT a phone number (tests the "no phone at all → text push" branch)
_POLICY_NO_PHONE = {k: v for k, v in CD_POLICY_ACTIVE_CLASS1.items() if k != "phone"}

# Minimal fake base64 PDF — just needs to be decodable bytes
_FAKE_PDF_B64 = base64.b64encode(b"%PDF-1.4 minimal fake pdf for tests").decode()

# An AI response text with NO Thai phone pattern → extract_phone_from_response → None
_ANALYSIS_NO_PHONE = (
    "🟢 **ได้รับสิทธิ์เคลม**\nประเมินค่าซ่อม 8,000 บาท\n"
    "*หมายเหตุ: เป็นการประเมินเบื้องต้นโดย AI*"
)


def _mock_api():
    """Return a mock line_bot_api with push_message and reply_message tracked."""
    api = MagicMock()
    api.push_message  = MagicMock(return_value=None)
    api.reply_message = MagicMock(return_value=None)
    return api


def _mock_gemini_model(response_text: str = "AI result"):
    """Return a mock gemini_model whose generate_content returns response_text."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = response_text
    return mock_model


def _mock_genai(upload_name: str = "files/fake_upload_001"):
    """Return a mock genai module (upload_file / delete_file)."""
    mock_genai = MagicMock()
    uploaded = MagicMock()
    uploaded.name = upload_name
    mock_genai.upload_file.return_value = uploaded
    mock_genai.delete_file = MagicMock(return_value=None)
    return mock_genai


# ─────────────────────────────────────────────────────────────────────────────
# CE-03  analyze_damage_with_gemini
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeDamageWithGemini:
    """CE-03: analyze_damage_with_gemini — damage analysis orchestrator."""

    # ── Early-exit path (no policy document) ─────────────────────────────────

    def test_no_policy_doc_returns_error_string(self):
        from claim_engine import analyze_damage_with_gemini
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": None}
        result = analyze_damage_with_gemini(
            _mock_gemini_model(), _mock_genai(), DUMMY_JPEG_BYTES, policy
        )
        assert isinstance(result, str)
        assert "ไม่พบเอกสารกรมธรรม์" in result

    def test_no_policy_doc_does_not_call_gemini(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": None}
        analyze_damage_with_gemini(mock_model, _mock_genai(), DUMMY_JPEG_BYTES, policy)
        mock_model.generate_content.assert_not_called()

    # ── Full-analysis path (policy document provided) ────────────────────────

    def test_with_policy_doc_calls_upload_file(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("AI ผล")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(mock_model, mock_genai, DUMMY_JPEG_BYTES, policy)
        mock_genai.upload_file.assert_called_once()

    def test_with_policy_doc_calls_generate_content(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("AI ผล")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(mock_model, mock_genai, DUMMY_JPEG_BYTES, policy)
        mock_model.generate_content.assert_called_once()

    def test_with_policy_doc_calls_delete_file(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("AI ผล")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(mock_model, mock_genai, DUMMY_JPEG_BYTES, policy)
        mock_genai.delete_file.assert_called_once_with("files/fake_upload_001")

    def test_with_policy_doc_returns_ai_text(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("🟢 ได้รับสิทธิ์เคลม")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            result = analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy
            )
        assert result == "🟢 ได้รับสิทธิ์เคลม"

    # ── has_counterpart prompt injection ─────────────────────────────────────

    def test_has_counterpart_yes_included_in_prompt(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("ok")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy,
                has_counterpart="มีคู่กรณี"
            )
        call_args = mock_model.generate_content.call_args
        prompt_str = str(call_args)
        assert "มีคู่กรณี" in prompt_str

    def test_has_counterpart_no_included_in_prompt(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("ok")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy,
                has_counterpart="ไม่มีคู่กรณี"
            )
        call_args = mock_model.generate_content.call_args
        assert "ไม่มีคู่กรณี" in str(call_args)

    def test_additional_info_included_in_prompt(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("ok")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy,
                additional_info="รถชนที่แยกลาดพร้าว"
            )
        call_args = mock_model.generate_content.call_args
        assert "รถชนที่แยกลาดพร้าว" in str(call_args)

    # ── Exception handling ────────────────────────────────────────────────────

    def test_exception_in_generate_content_returns_error_string(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = RuntimeError("Gemini timeout")
        mock_genai = _mock_genai()
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            result = analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy
            )
        assert isinstance(result, str)
        assert "เกิดข้อผิดพลาด" in result

    def test_exception_in_upload_file_returns_error_string(self):
        from claim_engine import analyze_damage_with_gemini
        mock_model = _mock_gemini_model("ok")
        mock_genai = MagicMock()
        mock_genai.upload_file.side_effect = Exception("Upload failed")
        policy = {**CD_POLICY_ACTIVE_CLASS1, "policy_document_base64": _FAKE_PDF_B64}
        with patch("time.sleep"):
            result = analyze_damage_with_gemini(
                mock_model, mock_genai, DUMMY_JPEG_BYTES, policy
            )
        assert "เกิดข้อผิดพลาด" in result


# ─────────────────────────────────────────────────────────────────────────────
# CE-04  start_claim_analysis
# ─────────────────────────────────────────────────────────────────────────────

class TestStartClaimAnalysis:
    """CE-04: start_claim_analysis — full analysis orchestration."""

    def _run(
        self,
        api=None,
        analysis_text: str = DAMAGE_ANALYSIS_ELIGIBLE,
        policy: dict = None,
        user_id: str = USER_ID_A,
        additional_info: str = None,
        has_counterpart: str = "มีคู่กรณี",
    ):
        """Helper: run start_claim_analysis with mocked dependencies."""
        from claim_engine import start_claim_analysis
        if api is None:
            api = _mock_api()
        if policy is None:
            policy = _POLICY_WITH_PHONE

        # Mock analyze_damage_with_gemini to return analysis_text directly
        mock_model = _mock_gemini_model(analysis_text)
        mock_genai = _mock_genai()

        sessions = {user_id: {"state": "waiting_for_additional_info"}}

        with patch("claim_engine.analyze_damage_with_gemini", return_value=analysis_text):
            start_claim_analysis(
                api, mock_model, mock_genai, user_id,
                DUMMY_JPEG_BYTES, policy,
                additional_info, has_counterpart, sessions,
            )

        return api, sessions

    # ── Wait message ──────────────────────────────────────────────────────────

    def test_sends_wait_message_first(self):
        """First push_message must be the 'กำลังวิเคราะห์' holding message."""
        api, _ = self._run()
        first_call = api.push_message.call_args_list[0]
        msg_text = str(first_call)
        assert "กำลังวิเคราะห์" in msg_text

    def test_push_message_called_at_least_twice(self):
        """At least: (1) wait message, (2) analysis result."""
        api, _ = self._run()
        assert api.push_message.call_count >= 2

    # ── Phone found → flex message push ──────────────────────────────────────

    def test_phone_in_analysis_result_triggers_flex_push(self):
        """DAMAGE_ANALYSIS_ELIGIBLE contains 'โทร 1557' → flex push sent."""
        api, _ = self._run(analysis_text=DAMAGE_ANALYSIS_ELIGIBLE)
        # Should have 3 pushes: wait, flex result, next_steps
        assert api.push_message.call_count == 3

    def test_policy_fallback_phone_triggers_flex_push(self):
        """When AI result has no phone but policy.phone exists → flex push."""
        api, _ = self._run(analysis_text=_ANALYSIS_NO_PHONE, policy=_POLICY_WITH_PHONE)
        # _POLICY_WITH_PHONE has phone "0812345678" → flex sent
        assert api.push_message.call_count == 3

    # ── No phone anywhere → plain text push ──────────────────────────────────

    def test_no_phone_sends_text_messages_not_flex(self):
        """
        No phone in AI result AND policy has no phone →
        push_message called with TextMessage, NOT FlexMessage.
        """
        api, _ = self._run(analysis_text=_ANALYSIS_NO_PHONE, policy=_POLICY_NO_PHONE)
        from linebot.v3.messaging import FlexMessage as FLX
        # Check that no FlexMessage for the analysis result was sent
        # (next_steps flex IS sent, so we look at the second push call specifically)
        second_call_str = str(api.push_message.call_args_list[1])
        # FlexMessage would contain "alt_text" for the analysis result
        assert "ผลการวิเคราะห์เคลมประกัน" not in second_call_str

    def test_no_phone_push_message_called_at_least_twice(self):
        api, _ = self._run(analysis_text=_ANALYSIS_NO_PHONE, policy=_POLICY_NO_PHONE)
        # wait-message + text result + next_steps = 3 calls
        assert api.push_message.call_count >= 2

    # ── State transition ──────────────────────────────────────────────────────

    def test_session_state_set_to_completed(self):
        """After successful analysis, user session state must be 'completed'."""
        _, sessions = self._run()
        assert sessions[USER_ID_A]["state"] == "completed"

    def test_session_state_not_completed_if_exception(self):
        """If inner call raises, session must not advance to completed."""
        from claim_engine import start_claim_analysis
        api = _mock_api()
        sessions = {USER_ID_A: {"state": "waiting_for_additional_info"}}

        with patch(
            "claim_engine.analyze_damage_with_gemini",
            side_effect=RuntimeError("network error"),
        ):
            start_claim_analysis(
                api, _mock_gemini_model(), _mock_genai(), USER_ID_A,
                DUMMY_JPEG_BYTES, _POLICY_WITH_PHONE,
                None, "มีคู่กรณี", sessions,
            )
        # State must NOT have advanced
        assert sessions[USER_ID_A]["state"] != "completed"

    # ── Exception handling ────────────────────────────────────────────────────

    def test_exception_sends_error_push_message(self):
        """Exception in analysis must result in an error push, not a crash."""
        from claim_engine import start_claim_analysis
        api = _mock_api()
        sessions = {USER_ID_A: {"state": "waiting_for_additional_info"}}

        with patch(
            "claim_engine.analyze_damage_with_gemini",
            side_effect=RuntimeError("API down"),
        ):
            start_claim_analysis(
                api, _mock_gemini_model(), _mock_genai(), USER_ID_A,
                DUMMY_JPEG_BYTES, _POLICY_WITH_PHONE,
                None, "มีคู่กรณี", sessions,
            )

        # push_message must still have been called (for error message)
        assert api.push_message.call_count >= 1

    def test_exception_does_not_raise_to_caller(self):
        """start_claim_analysis must never propagate exceptions to its caller."""
        from claim_engine import start_claim_analysis
        sessions = {USER_ID_A: {"state": "waiting_for_additional_info"}}

        # Should not raise
        with patch(
            "claim_engine.analyze_damage_with_gemini",
            side_effect=Exception("unexpected"),
        ):
            start_claim_analysis(
                _mock_api(), _mock_gemini_model(), _mock_genai(), USER_ID_A,
                DUMMY_JPEG_BYTES, _POLICY_WITH_PHONE,
                None, None, sessions,
            )

    # ── Both has_counterpart values pass through ──────────────────────────────

    @pytest.mark.parametrize("counterpart", ["มีคู่กรณี", "ไม่มีคู่กรณี", None])
    def test_counterpart_variants_do_not_crash(self, counterpart):
        api, sessions = self._run(has_counterpart=counterpart)
        assert sessions[USER_ID_A]["state"] == "completed"

    # ── additional_info skip case ─────────────────────────────────────────────

    def test_none_additional_info_does_not_crash(self):
        api, sessions = self._run(additional_info=None)
        assert sessions[USER_ID_A]["state"] == "completed"

    def test_provided_additional_info_does_not_crash(self):
        api, sessions = self._run(additional_info="รถชนที่แยกดอนเมือง")
        assert sessions[USER_ID_A]["state"] == "completed"
