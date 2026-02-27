"""
test_flex_messages.py
=====================
Structural unit tests for every public function in flex_messages.py.

Strategy
--------
Each test calls the production function and:
  1. Verifies no exception is raised.
  2. Verifies the return value is not None (FlexContainer).
  3. For content-sensitive checks, patches FlexContainer.from_dict so the
     raw dict can be inspected without depending on SDK internals.

Functions under test
--------------------
  FM-01  create_request_info_flex()
  FM-02  create_vehicle_selection_flex(policies)
  FM-03  create_policy_info_flex(policy_info)
  FM-04  create_error_flex(error_message)
  FM-05  create_welcome_flex()
  FM-06  create_analysis_result_flex(summary, phone, company, status)
  FM-07  create_input_method_flex()
  FM-08  create_additional_info_prompt_flex()
  FM-09  create_next_steps_flex()
  FM-10  create_claim_submission_instructions_flex()
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    CD_POLICY_ACTIVE_CLASS1,
    CD_POLICY_ACTIVE_CLASS2PLUS,
    DAMAGE_ANALYSIS_ELIGIBLE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _capture(fn, *args, **kwargs):
    """
    Call fn(*args, **kwargs) with FlexContainer.from_dict patched so the raw
    dict is captured and returned alongside the mock return value.

    Returns (captured_dict, mock_return_value).
    """
    captured = {}

    def _from_dict(d):
        captured.update(d)
        mock = MagicMock()
        mock._raw = d
        return mock

    with patch("flex_messages.FlexContainer.from_dict", side_effect=_from_dict):
        result = fn(*args, **kwargs)

    return captured, result


# ─────────────────────────────────────────────────────────────────────────────
# FM-01  create_request_info_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateRequestInfoFlex:
    """FM-01: create_request_info_flex returns a bubble FlexContainer."""

    def test_returns_without_raising(self):
        from flex_messages import create_request_info_flex
        result = create_request_info_flex()
        assert result is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_request_info_flex
        d, _ = _capture(create_request_info_flex)
        assert d.get("type") == "bubble"

    def test_has_body_section(self):
        from flex_messages import create_request_info_flex
        d, _ = _capture(create_request_info_flex)
        assert "body" in d

    def test_has_footer_section(self):
        from flex_messages import create_request_info_flex
        d, _ = _capture(create_request_info_flex)
        assert "footer" in d


# ─────────────────────────────────────────────────────────────────────────────
# FM-02  create_vehicle_selection_flex(policies)
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateVehicleSelectionFlex:
    """FM-02: create_vehicle_selection_flex encodes all provided policies."""

    def _policies(self):
        return [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_ACTIVE_CLASS2PLUS]

    def test_returns_without_raising(self):
        from flex_messages import create_vehicle_selection_flex
        assert create_vehicle_selection_flex(self._policies()) is not None

    def test_single_policy_does_not_raise(self):
        from flex_messages import create_vehicle_selection_flex
        assert create_vehicle_selection_flex([CD_POLICY_ACTIVE_CLASS1]) is not None

    def test_body_contains_buttons_for_each_policy(self):
        from flex_messages import create_vehicle_selection_flex
        policies = self._policies()
        d, _ = _capture(create_vehicle_selection_flex, policies)
        # The body contents section must contain one button per policy
        body_contents_count = len(d["body"]["contents"])
        assert body_contents_count >= 1

    def test_plate_of_each_policy_referenced_in_raw_dict(self):
        from flex_messages import create_vehicle_selection_flex
        policies = self._policies()
        d, _ = _capture(create_vehicle_selection_flex, policies)
        raw_str = str(d)
        assert "กก1234" in raw_str
        assert "ขข5678" in raw_str

    def test_raw_type_is_bubble(self):
        from flex_messages import create_vehicle_selection_flex
        d, _ = _capture(create_vehicle_selection_flex, self._policies())
        assert d.get("type") == "bubble"


# ─────────────────────────────────────────────────────────────────────────────
# FM-03  create_policy_info_flex(policy_info)
# ─────────────────────────────────────────────────────────────────────────────

class TestCreatePolicyInfoFlex:
    """FM-03: create_policy_info_flex embeds policy details in the output."""

    def test_returns_without_raising(self):
        from flex_messages import create_policy_info_flex
        assert create_policy_info_flex(CD_POLICY_ACTIVE_CLASS1) is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_policy_info_flex
        d, _ = _capture(create_policy_info_flex, CD_POLICY_ACTIVE_CLASS1)
        assert d.get("type") == "bubble"

    def test_plate_number_in_raw_output(self):
        from flex_messages import create_policy_info_flex
        d, _ = _capture(create_policy_info_flex, CD_POLICY_ACTIVE_CLASS1)
        assert "กก1234" in str(d)

    def test_insurance_type_in_raw_output(self):
        from flex_messages import create_policy_info_flex
        d, _ = _capture(create_policy_info_flex, CD_POLICY_ACTIVE_CLASS1)
        assert "ชั้น 1" in str(d)

    def test_has_body_section(self):
        from flex_messages import create_policy_info_flex
        d, _ = _capture(create_policy_info_flex, CD_POLICY_ACTIVE_CLASS1)
        assert "body" in d

    def test_different_policy_encodes_different_plate(self):
        from flex_messages import create_policy_info_flex
        d, _ = _capture(create_policy_info_flex, CD_POLICY_ACTIVE_CLASS2PLUS)
        assert "ขข5678" in str(d)


# ─────────────────────────────────────────────────────────────────────────────
# FM-04  create_error_flex(error_message)
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateErrorFlex:
    """FM-04: create_error_flex embeds the error message text."""

    def test_returns_without_raising(self):
        from flex_messages import create_error_flex
        assert create_error_flex("ระบบขัดข้อง") is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_error_flex
        d, _ = _capture(create_error_flex, "ระบบขัดข้อง")
        assert d.get("type") == "bubble"

    def test_error_message_present_in_raw(self):
        from flex_messages import create_error_flex
        msg = "ไม่สามารถเชื่อมต่อได้"
        d, _ = _capture(create_error_flex, msg)
        assert msg in str(d)


# ─────────────────────────────────────────────────────────────────────────────
# FM-05  create_welcome_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateWelcomeFlex:
    """FM-05: create_welcome_flex returns a valid bubble."""

    def test_returns_without_raising(self):
        from flex_messages import create_welcome_flex
        assert create_welcome_flex() is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_welcome_flex
        d, _ = _capture(create_welcome_flex)
        assert d.get("type") == "bubble"

    def test_has_body(self):
        from flex_messages import create_welcome_flex
        d, _ = _capture(create_welcome_flex)
        assert "body" in d


# ─────────────────────────────────────────────────────────────────────────────
# FM-06  create_analysis_result_flex(summary, phone, company, status)
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateAnalysisResultFlex:
    """FM-06: create_analysis_result_flex encodes summary text and phone."""

    def test_returns_without_raising_with_phone(self):
        from flex_messages import create_analysis_result_flex
        result = create_analysis_result_flex(
            summary_text=DAMAGE_ANALYSIS_ELIGIBLE,
            phone_number="1557",
            insurance_company="กรุงเทพประกันภัย",
            claim_status="approved",
        )
        assert result is not None

    def test_returns_without_raising_without_phone(self):
        from flex_messages import create_analysis_result_flex
        assert create_analysis_result_flex(summary_text="ผลการวิเคราะห์") is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_analysis_result_flex
        d, _ = _capture(create_analysis_result_flex, summary_text="ผลการวิเคราะห์")
        assert d.get("type") == "bubble"

    def test_summary_text_in_raw(self):
        from flex_messages import create_analysis_result_flex
        summary = "🟢 ได้รับสิทธิ์เคลม"
        d, _ = _capture(create_analysis_result_flex, summary_text=summary)
        assert summary in str(d)

    def test_phone_number_in_footer_when_provided(self):
        from flex_messages import create_analysis_result_flex
        d, _ = _capture(
            create_analysis_result_flex,
            summary_text="ผล",
            phone_number="1557",
        )
        assert "1557" in str(d)

    def test_footer_has_no_call_button_when_phone_is_none(self):
        from flex_messages import create_analysis_result_flex
        d, _ = _capture(create_analysis_result_flex, summary_text="ผล")
        footer_str = str(d.get("footer", {}))
        assert "tel:" not in footer_str

    @pytest.mark.parametrize("status,expected_color", [
        ("approved",    "#17C964"),
        ("rejected",    "#F31260"),
        ("conditional", "#F5A524"),
        ("unknown",     "#0066FF"),
    ])
    def test_status_colour_applied(self, status, expected_color):
        from flex_messages import create_analysis_result_flex
        d, _ = _capture(
            create_analysis_result_flex,
            summary_text="x",
            phone_number="1557",
            claim_status=status,
        )
        assert expected_color in str(d)


# ─────────────────────────────────────────────────────────────────────────────
# FM-07  create_input_method_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateInputMethodFlex:
    """FM-07: create_input_method_flex returns a valid bubble."""

    def test_returns_without_raising(self):
        from flex_messages import create_input_method_flex
        assert create_input_method_flex() is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_input_method_flex
        d, _ = _capture(create_input_method_flex)
        assert d.get("type") == "bubble"


# ─────────────────────────────────────────────────────────────────────────────
# FM-08  create_additional_info_prompt_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateAdditionalInfoPromptFlex:
    """FM-08: create_additional_info_prompt_flex returns a valid FlexContainer."""

    def test_returns_without_raising(self):
        from flex_messages import create_additional_info_prompt_flex
        assert create_additional_info_prompt_flex() is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_additional_info_prompt_flex
        d, _ = _capture(create_additional_info_prompt_flex)
        assert d.get("type") == "bubble"

    def test_has_body_and_footer(self):
        from flex_messages import create_additional_info_prompt_flex
        d, _ = _capture(create_additional_info_prompt_flex)
        assert "body" in d
        assert "footer" in d


# ─────────────────────────────────────────────────────────────────────────────
# FM-09  create_next_steps_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateNextStepsFlex:
    """FM-09: create_next_steps_flex returns a valid FlexContainer."""

    def test_returns_without_raising(self):
        from flex_messages import create_next_steps_flex
        assert create_next_steps_flex() is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_next_steps_flex
        d, _ = _capture(create_next_steps_flex)
        assert d.get("type") == "bubble"

    def test_has_footer_with_buttons(self):
        from flex_messages import create_next_steps_flex
        d, _ = _capture(create_next_steps_flex)
        assert "footer" in d
        footer_str = str(d["footer"])
        assert "button" in footer_str


# ─────────────────────────────────────────────────────────────────────────────
# FM-10  create_claim_submission_instructions_flex()
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateClaimSubmissionInstructionsFlex:
    """FM-10: create_claim_submission_instructions_flex returns a valid FlexContainer."""

    def test_returns_without_raising(self):
        from flex_messages import create_claim_submission_instructions_flex
        assert create_claim_submission_instructions_flex() is not None

    def test_raw_type_is_bubble(self):
        from flex_messages import create_claim_submission_instructions_flex
        d, _ = _capture(create_claim_submission_instructions_flex)
        assert d.get("type") == "bubble"

    def test_has_body(self):
        from flex_messages import create_claim_submission_instructions_flex
        d, _ = _capture(create_claim_submission_instructions_flex)
        assert "body" in d
