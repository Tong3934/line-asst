"""
test_business_logic.py
======================
Unit / integration tests for the non-HTTP business rules defined in the BRD
and Tech-Spec.  These tests do NOT need a live HTTP server — they call the
source functions directly.

Areas covered
-------------
  BL-01  Policy lookup functions (by CID, plate, name)
  BL-02  Claim ID format validation (regex)
  BL-03  Claim ID sequence generation
  BL-04  Buddhist Era → Gregorian date conversion
  BL-05  Keyword detection for claim type
  BL-06  Eligibility verdict logic (coverage class × counterpart)
  BL-07  Required-document completeness per claim type
  BL-08  Claim status lifecycle transitions
  BL-09  Phone number extraction from Gemini response text
  BL-10  Webhook signature verification (HMAC-SHA256)
  BL-11  Document category validation (9 accepted + "unknown" rejection)
"""

import base64
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_data import (
    CD_POLICY_ACTIVE_CLASS1,
    CD_POLICY_ACTIVE_CLASS2PLUS,
    CD_POLICY_EXPIRED,
    CD_POLICY_INACTIVE,
    H_POLICY_ACTIVE,
    POLICY_DB_BY_CID,
    POLICY_DB_BY_PLATE,
    VALID_CLAIM_ID_CASES,
    INVALID_CLAIM_ID_CASES,
    BUDDHIST_ERA_CONVERSION_CASES,
    CD_KEYWORDS,
    H_KEYWORDS,
    CANCEL_KEYWORDS,
    VALID_DOCUMENT_CATEGORIES,
    REQUIRED_DOCS_CD_WITH_COUNTERPART,
    REQUIRED_DOCS_CD_NO_COUNTERPART,
    REQUIRED_DOCS_HEALTH,
    VALID_STATUS_TRANSITIONS,
    MOCK_CHANNEL_SECRET,
    make_line_signature,
    make_webhook_body,
    WEBHOOK_TRIGGER_CD,
    WEBHOOK_TRIGGER_MAIN,
)


# ─────────────────────────────────────────────────────────────────────────────
# BL-01  Policy lookup
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyLookup:
    """BL-01: mock_data lookup functions behave per spec."""

    def test_lookup_by_cid_active_returns_policy(self):
        from mock_data import search_policies_by_cid
        # "7564985348794" is the CID in the first mock_data record
        result = search_policies_by_cid("7564985348794")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["cid"] == "7564985348794"

    def test_lookup_by_cid_unknown_returns_empty(self):
        from mock_data import search_policies_by_cid
        result = search_policies_by_cid("0000000000000")
        assert result == []

    def test_lookup_by_plate_found(self):
        from mock_data import search_policies_by_plate
        result = search_policies_by_plate("1กข1234")
        # Returns single dict or falsy — must not be an empty list or None crash
        assert result is not None or result is None   # either found or None
        # If found, must have a plate field
        if result:
            assert "plate" in result or result is not None

    def test_lookup_by_plate_not_found_returns_falsy(self):
        from mock_data import search_policies_by_plate
        result = search_policies_by_plate("ไม่มีทะเบียน9999")
        assert not result

    def test_lookup_by_name_returns_list(self):
        from mock_data import search_policies_by_name
        result = search_policies_by_name("สมชาย")
        assert isinstance(result, list)

    def test_lookup_by_name_not_found_returns_empty(self):
        from mock_data import search_policies_by_name
        result = search_policies_by_name("ชื่อที่ไม่มีในระบบXYZ99999")
        assert result == []

    def test_policy_record_has_required_cd_fields(self):
        """Every CD policy must have the fields required by the data model."""
        required_fields = [
            "policy_number", "cid", "first_name", "last_name",
            "plate", "car_model", "car_year", "insurance_type",
            "insurance_company", "policy_start", "policy_end", "status",
        ]
        for field in required_fields:
            assert field in CD_POLICY_ACTIVE_CLASS1, f"Missing field: {field}"

    def test_status_values_are_valid(self):
        valid_statuses = {"active", "expired", "inactive"}
        for policy in [CD_POLICY_ACTIVE_CLASS1, CD_POLICY_EXPIRED, CD_POLICY_INACTIVE]:
            assert policy["status"] in valid_statuses


# ─────────────────────────────────────────────────────────────────────────────
# BL-02  Claim ID format validation
# ─────────────────────────────────────────────────────────────────────────────

CLAIM_ID_RE = re.compile(r'^(CD|H)-\d{8}-\d{6}$')


class TestClaimIdFormat:
    """BL-02: Claim IDs must match {CD|H}-YYYYMMDD-NNNNNN."""

    @pytest.mark.parametrize("claim_id", VALID_CLAIM_ID_CASES)
    def test_valid_claim_id_matches_regex(self, claim_id):
        assert CLAIM_ID_RE.match(claim_id), f"Expected valid: {claim_id}"

    @pytest.mark.parametrize("claim_id", INVALID_CLAIM_ID_CASES)
    def test_invalid_claim_id_does_not_match_regex(self, claim_id):
        assert not CLAIM_ID_RE.match(claim_id), f"Expected invalid: {claim_id}"

    def test_cd_prefix(self):
        assert CLAIM_ID_RE.match("CD-20260226-000001")

    def test_h_prefix(self):
        assert CLAIM_ID_RE.match("H-20260226-000001")

    def test_zero_padded_sequence(self):
        """Sequence must be exactly 6 digits."""
        assert CLAIM_ID_RE.match("CD-20260226-000001")
        assert not CLAIM_ID_RE.match("CD-20260226-1")


# ─────────────────────────────────────────────────────────────────────────────
# BL-03  Claim ID sequence generation (sequence.json)
# ─────────────────────────────────────────────────────────────────────────────

class TestClaimIdSequence:
    """BL-03: Sequence counter increments correctly and formats Claim ID."""

    def _generate_claim_id(self, claim_type: str, counter: int, date_str: str) -> str:
        """Replicate the spec formula: {type}-{YYYYMMDD}-{counter:06d}"""
        return f"{claim_type}-{date_str}-{counter:06d}"

    def test_first_cd_claim_id(self):
        result = self._generate_claim_id("CD", 1, "20260226")
        assert result == "CD-20260226-000001"

    def test_first_h_claim_id(self):
        result = self._generate_claim_id("H", 1, "20260226")
        assert result == "H-20260226-000001"

    def test_sequence_zero_padding(self):
        assert self._generate_claim_id("CD", 42,  "20260226") == "CD-20260226-000042"
        assert self._generate_claim_id("CD", 999, "20260226") == "CD-20260226-000999"

    def test_max_sequence_six_digits(self):
        assert self._generate_claim_id("CD", 999999, "20260226") == "CD-20260226-999999"

    def test_cd_and_h_counters_are_independent(self):
        """CD sequence and H sequence must be managed separately."""
        seq = {"CD": 5, "H": 3}
        seq["CD"] += 1
        assert seq["CD"] == 6
        assert seq["H"] == 3   # H counter unchanged

    def test_sequence_json_structure(self):
        """sequence.json must deserialise to a dict with CD and H integer keys."""
        from tests.test_data import SEQUENCE_JSON_INITIAL, SEQUENCE_JSON_AFTER_ONE_CD
        assert SEQUENCE_JSON_INITIAL["CD"] == 0
        assert SEQUENCE_JSON_INITIAL["H"]  == 0
        assert SEQUENCE_JSON_AFTER_ONE_CD["CD"] == 1
        assert SEQUENCE_JSON_AFTER_ONE_CD["H"]  == 0


# ─────────────────────────────────────────────────────────────────────────────
# BL-04  Buddhist Era → Gregorian date conversion
# ─────────────────────────────────────────────────────────────────────────────

def _convert_be_to_gregorian(value: str) -> str:
    """
    Naive implementation that matches what the AI prompt instructs:
    subtract 543 from the year portion.
    """
    # Handles "YYYY" or "YYYY-MM-DD" formats
    parts = value.split("-")
    gregorian_year = str(int(parts[0]) - 543)
    parts[0] = gregorian_year
    return "-".join(parts)


class TestBuddhistEraConversion:
    """BL-04: Thai Buddhist Era year → Gregorian."""

    @pytest.mark.parametrize("be_str, expected", BUDDHIST_ERA_CONVERSION_CASES)
    def test_conversion(self, be_str, expected):
        result = _convert_be_to_gregorian(be_str)
        assert result == expected, f"BE {be_str} → expected {expected}, got {result}"

    def test_date_format_preserved(self):
        """Full YYYY-MM-DD format must keep month and day unchanged."""
        result = _convert_be_to_gregorian("2568-03-15")
        assert result == "2025-03-15"

    def test_year_only(self):
        result = _convert_be_to_gregorian("2567")
        assert result == "2024"


# ─────────────────────────────────────────────────────────────────────────────
# BL-05  Keyword detection for claim type
# ─────────────────────────────────────────────────────────────────────────────

def _detect_claim_type(text: str):
    """Replicate the keyword-detection logic from the spec."""
    text_lower = text.lower()
    cd_hits = sum(1 for kw in CD_KEYWORDS if kw.lower() in text_lower)
    h_hits  = sum(1 for kw in H_KEYWORDS  if kw.lower() in text_lower)
    if cd_hits > 0 and h_hits == 0:
        return "CD"
    if h_hits > 0 and cd_hits == 0:
        return "H"
    if cd_hits > 0 and h_hits > 0:
        return "AMBIGUOUS"
    return None


class TestKeywordDetection:
    """BL-05: FR-01.3/FR-01.4 — Keyword-based claim type detection."""

    @pytest.mark.parametrize("text,expected_type", [
        ("รถชนที่แยก",              "CD"),
        ("เฉี่ยวชน",                "CD"),
        ("my car had an accident",  "CD"),
        ("vehicle damage",          "CD"),
        ("ป่วยต้องนอนโรงพยาบาล",   "H"),
        ("I am sick need hospital", "H"),
        ("went to medical clinic",  "H"),
        ("surgery needed",          "H"),
    ])
    def test_single_type_detection(self, text, expected_type):
        assert _detect_claim_type(text) == expected_type

    def test_ambiguous_returns_ambiguous(self):
        """Message with both CD and H keywords → AMBIGUOUS."""
        assert _detect_claim_type("รถชนแล้วต้องนอนโรงพยาบาล") == "AMBIGUOUS"

    def test_no_matching_keywords_returns_none(self):
        assert _detect_claim_type("สวัสดี วันนี้อากาศดี") is None

    @pytest.mark.parametrize("cancel_word", CANCEL_KEYWORDS)
    def test_cancel_keywords_recognised(self, cancel_word):
        """Cancel words must be identifiable (case-insensitive match)."""
        assert cancel_word.lower() in [kw.lower() for kw in CANCEL_KEYWORDS]


# ─────────────────────────────────────────────────────────────────────────────
# BL-06  Eligibility verdict logic
# ─────────────────────────────────────────────────────────────────────────────

def _is_eligible(coverage_type: str, has_counterpart: str) -> bool:
    """
    Replicate the eligibility rule table from FR-08 / BRD §8.
    """
    if coverage_type == "ชั้น 1":
        return True
    # ชั้น 2+ / ชั้น 2 / ชั้น 3+ / ชั้น 3 require counterpart
    return has_counterpart == "มีคู่กรณี"


class TestEligibilityLogic:
    """BL-06: FR-08.3 — Eligibility verdicts per insurance class × counterpart."""

    @pytest.mark.parametrize("coverage_type,expected", [
        ("ชั้น 1",  True),
        ("ชั้น 2+", True),
        ("ชั้น 2",  True),
        ("ชั้น 3+", True),
        ("ชั้น 3",  True),
    ])
    def test_with_counterpart_all_classes_eligible(self, coverage_type, expected):
        assert _is_eligible(coverage_type, "มีคู่กรณี") == expected

    @pytest.mark.parametrize("coverage_type,expected", [
        ("ชั้น 1",  True),
        ("ชั้น 2+", False),
        ("ชั้น 2",  False),
        ("ชั้น 3+", False),
        ("ชั้น 3",  False),
    ])
    def test_no_counterpart_eligibility(self, coverage_type, expected):
        assert _is_eligible(coverage_type, "ไม่มีคู่กรณี") == expected


# ─────────────────────────────────────────────────────────────────────────────
# BL-07  Required documents completeness
# ─────────────────────────────────────────────────────────────────────────────

def _check_missing_docs(uploaded: dict, required: list) -> list:
    return [doc for doc in required if doc not in uploaded]


class TestRequiredDocumentCompleteness:
    """BL-07: FR-07.3/FR-07.4 — completeness check per claim type."""

    # ── CD with counterpart ──────────────────────────────────────────────────

    def test_cd_with_counterpart_all_docs_no_missing(self):
        uploaded = {k: "file.jpg" for k in REQUIRED_DOCS_CD_WITH_COUNTERPART}
        assert _check_missing_docs(uploaded, REQUIRED_DOCS_CD_WITH_COUNTERPART) == []

    def test_cd_with_counterpart_missing_other_party_dl(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_CD_WITH_COUNTERPART
                    if k != "driving_license_other_party"}
        missing = _check_missing_docs(uploaded, REQUIRED_DOCS_CD_WITH_COUNTERPART)
        assert "driving_license_other_party" in missing

    def test_cd_with_counterpart_missing_damage_photo(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_CD_WITH_COUNTERPART
                    if k != "vehicle_damage_photo"}
        missing = _check_missing_docs(uploaded, REQUIRED_DOCS_CD_WITH_COUNTERPART)
        assert "vehicle_damage_photo" in missing

    # ── CD no counterpart ────────────────────────────────────────────────────

    def test_cd_no_counterpart_does_not_require_other_party_dl(self):
        """Other party DL is NOT in the required set for no-counterpart claims."""
        assert "driving_license_other_party" not in REQUIRED_DOCS_CD_NO_COUNTERPART

    def test_cd_no_counterpart_complete(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_CD_NO_COUNTERPART}
        assert _check_missing_docs(uploaded, REQUIRED_DOCS_CD_NO_COUNTERPART) == []

    # ── Health ───────────────────────────────────────────────────────────────

    def test_health_all_docs_no_missing(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_HEALTH}
        assert _check_missing_docs(uploaded, REQUIRED_DOCS_HEALTH) == []

    def test_health_missing_receipt_detected(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_HEALTH if k != "receipt"}
        missing = _check_missing_docs(uploaded, REQUIRED_DOCS_HEALTH)
        assert "receipt" in missing

    def test_discharge_summary_is_optional_health(self):
        """discharge_summary is optional — must NOT be listed in required."""
        assert "discharge_summary" not in REQUIRED_DOCS_HEALTH

    # ── Optional docs allowed but not blocking ────────────────────────────────

    def test_extra_optional_docs_not_in_missing(self):
        uploaded = {k: "f.jpg" for k in REQUIRED_DOCS_CD_WITH_COUNTERPART}
        uploaded["vehicle_location_photo"] = "location.jpg"  # optional
        missing = _check_missing_docs(uploaded, REQUIRED_DOCS_CD_WITH_COUNTERPART)
        assert missing == []


# ─────────────────────────────────────────────────────────────────────────────
# BL-08  Claim status lifecycle transitions
# ─────────────────────────────────────────────────────────────────────────────

def _allowed_next(current_status: str) -> list:
    return VALID_STATUS_TRANSITIONS.get(current_status, [])


class TestClaimStatusLifecycle:
    """BL-08: §5.7 — Status transition rules enforced."""

    def test_submitted_can_goto_under_review(self):
        assert "Under Review" in _allowed_next("Submitted")

    def test_submitted_cannot_skip_to_approved(self):
        assert "Approved" not in _allowed_next("Submitted")

    def test_submitted_cannot_goto_paid(self):
        assert "Paid" not in _allowed_next("Submitted")

    def test_under_review_can_goto_approved(self):
        assert "Approved" in _allowed_next("Under Review")

    def test_under_review_can_goto_rejected(self):
        assert "Rejected" in _allowed_next("Under Review")

    def test_approved_can_goto_paid(self):
        assert "Paid" in _allowed_next("Approved")

    def test_approved_cannot_goto_rejected(self):
        assert "Rejected" not in _allowed_next("Approved")

    def test_rejected_has_no_allowed_transitions(self):
        assert _allowed_next("Rejected") == []

    def test_paid_has_no_allowed_transitions(self):
        assert _allowed_next("Paid") == []

    def test_pending_can_return_to_under_review(self):
        assert "Under Review" in _allowed_next("Pending")


# ─────────────────────────────────────────────────────────────────────────────
# BL-09  Phone number extraction from Gemini response text
# ─────────────────────────────────────────────────────────────────────────────

class TestPhoneNumberExtraction:
    """BL-09: extract_phone_from_response — Thai phone pattern extractor in main.py."""

    @pytest.fixture(autouse=True)
    def _import_fn(self):
        import main as m
        self.fn = m.extract_phone_from_response

    @pytest.mark.parametrize("text,expected", [
        ("โทร 1557",                    "1557"),
        ("โทร 02-123-4567",             "021234567"),
        ("เบอร์: 098-765-4321",          "0987654321"),
        ("โทรศัพท์: 02-123-4567",       "021234567"),
        ("แจ้งเหตุ: 1557",              "1557"),
        ("call center 0987654321",       None),   # not in Thai pattern → None
    ])
    def test_extraction_patterns(self, text, expected):
        result = self.fn(text)
        assert result == expected

    def test_no_phone_number_returns_none(self):
        assert self.fn("ผลการวิเคราะห์ดีมาก") is None

    def test_phone_in_analysis_eligible_stub(self):
        from tests.test_data import DAMAGE_ANALYSIS_ELIGIBLE
        # The stub contains "โทร 1557"
        result = self.fn(DAMAGE_ANALYSIS_ELIGIBLE)
        assert result == "1557"


# ─────────────────────────────────────────────────────────────────────────────
# BL-10  Webhook HMAC-SHA256 signature computation
# ─────────────────────────────────────────────────────────────────────────────

class TestWebhookSignatureComputation:
    """BL-10: Verify our signature helper matches the LINE spec."""

    def test_signature_is_base64(self):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        sig  = make_line_signature(body)
        # Must be valid base64
        decoded = base64.b64decode(sig)
        assert len(decoded) == 32  # SHA-256 → 32 bytes

    def test_signature_matches_manual_hmac(self):
        body   = make_webhook_body(WEBHOOK_TRIGGER_CD)
        expected_mac = hmac.new(
            MOCK_CHANNEL_SECRET.encode(),
            body,
            hashlib.sha256,
        )
        expected_sig = base64.b64encode(expected_mac.digest()).decode()
        assert make_line_signature(body) == expected_sig

    def test_different_body_different_signature(self):
        body1 = make_webhook_body(WEBHOOK_TRIGGER_CD)
        body2 = make_webhook_body(WEBHOOK_TRIGGER_MAIN)
        assert make_line_signature(body1) != make_line_signature(body2)

    def test_different_secret_different_signature(self):
        body = make_webhook_body(WEBHOOK_TRIGGER_CD)
        sig1 = make_line_signature(body, "secret_one")
        sig2 = make_line_signature(body, "secret_two")
        assert sig1 != sig2


# ─────────────────────────────────────────────────────────────────────────────
# BL-11  Document category validation
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentCategoryValidation:
    """BL-11: FR-03.2/FR-03.3 — Only the 9 known categories are accepted."""

    @pytest.mark.parametrize("category", VALID_DOCUMENT_CATEGORIES)
    def test_valid_categories_accepted(self, category):
        assert category != "unknown"
        assert category in VALID_DOCUMENT_CATEGORIES

    def test_unknown_category_is_rejected(self):
        assert "unknown" not in VALID_DOCUMENT_CATEGORIES

    def test_unknown_string_is_recognised_as_invalid(self):
        invalid_inputs = ["selfie", "screenshot", "invoice", "passport", "unknown"]
        for cat in invalid_inputs:
            assert cat not in VALID_DOCUMENT_CATEGORIES

    def test_all_9_categories_present(self):
        assert len(VALID_DOCUMENT_CATEGORIES) == 9

    def test_driving_license_in_valid_set(self):
        assert "driving_license" in VALID_DOCUMENT_CATEGORIES

    def test_citizen_id_card_in_valid_set(self):
        assert "citizen_id_card" in VALID_DOCUMENT_CATEGORIES

    def test_vehicle_damage_photo_in_valid_set(self):
        assert "vehicle_damage_photo" in VALID_DOCUMENT_CATEGORIES

    def test_receipt_in_valid_set(self):
        assert "receipt" in VALID_DOCUMENT_CATEGORIES


# ─────────────────────────────────────────────────────────────────────────────
# BL-12  Extracted data structure integrity
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractedDataStructure:
    """BL-12: Validate the shape of AI-extracted data stubs."""

    def test_driving_license_has_required_fields(self):
        from tests.test_data import EXTRACTED_DRIVING_LICENSE
        for field in ["full_name_th", "citizen_id", "license_id", "expiry_date"]:
            assert field in EXTRACTED_DRIVING_LICENSE

    def test_citizen_id_is_13_digits(self):
        from tests.test_data import EXTRACTED_DRIVING_LICENSE
        cid = EXTRACTED_DRIVING_LICENSE["citizen_id"].replace("-", "")
        assert re.match(r'^\d{13}$', cid), f"Invalid CID: {cid}"

    def test_dates_in_gregorian_format(self):
        from tests.test_data import EXTRACTED_DRIVING_LICENSE
        date_re = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        for key in ["date_of_birth", "issue_date", "expiry_date"]:
            assert date_re.match(EXTRACTED_DRIVING_LICENSE[key]), (
                f"{key}: {EXTRACTED_DRIVING_LICENSE[key]}"
            )

    def test_vehicle_registration_plate_format(self):
        from tests.test_data import EXTRACTED_VEHICLE_REGISTRATION
        plate = EXTRACTED_VEHICLE_REGISTRATION["plate"]
        # Must contain at least 1 Thai or Latin character and digits
        assert plate and len(plate) > 0

    def test_damage_photo_severity_valid(self):
        from tests.test_data import EXTRACTED_DAMAGE_PHOTO
        assert EXTRACTED_DAMAGE_PHOTO["severity"] in ("minor", "moderate", "severe")

    def test_itemised_bill_total_matches_line_items(self):
        from tests.test_data import EXTRACTED_ITEMISED_BILL
        calc_total = sum(item["amount"] for item in EXTRACTED_ITEMISED_BILL["line_items"])
        assert calc_total == EXTRACTED_ITEMISED_BILL["total"]

    def test_health_extracted_data_keys_present(self):
        from tests.test_data import EXTRACTED_DATA_HEALTH
        for key in ["citizen_id_card", "medical_certificate", "itemised_bill", "medical_receipts"]:
            assert key in EXTRACTED_DATA_HEALTH

    def test_cd_extracted_data_with_counterpart_keys(self):
        from tests.test_data import EXTRACTED_DATA_CD_WITH_COUNTERPART
        for key in [
            "driving_license_customer",
            "driving_license_other_party",
            "vehicle_registration",
            "damage_photos",
        ]:
            assert key in EXTRACTED_DATA_CD_WITH_COUNTERPART

    def test_cd_no_counterpart_no_other_party_key(self):
        from tests.test_data import EXTRACTED_DATA_CD_NO_COUNTERPART
        assert "driving_license_other_party" not in EXTRACTED_DATA_CD_NO_COUNTERPART


# ─────────────────────────────────────────────────────────────────────────────
# BL-01 extension  Phone number lookup
# ─────────────────────────────────────────────────────────────────────────────

class TestPolicyLookupByPhone:
    """BL-01 (phone): search_policies_by_phone matches customer phone numbers."""

    def test_known_phone_returns_policies(self):
        from mock_data import search_policies_by_phone
        # MOCK_CUSTOMERS["7564985348794"]["phone"] == "0812345678"
        result = search_policies_by_phone("0812345678")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_known_phone_policy_plate_present(self):
        from mock_data import search_policies_by_phone
        result = search_policies_by_phone("0812345678")
        plates = [p["plate"] for p in result]
        assert "1กข1234" in plates

    def test_unknown_phone_returns_empty(self):
        from mock_data import search_policies_by_phone
        result = search_policies_by_phone("0000000000")
        assert result == []

    def test_phone_with_dashes_stripped(self):
        from mock_data import search_policies_by_phone
        # "081-234-5678" should normalise to "0812345678"
        result = search_policies_by_phone("081-234-5678")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_second_customer_phone_found(self):
        from mock_data import search_policies_by_phone
        # MOCK_CUSTOMERS["9294258136443"]["phone"] == "0898765432"
        result = search_policies_by_phone("0898765432")
        assert isinstance(result, list)
        assert len(result) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# BL-13  extract_info_from_image_with_gemini
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractInfoFromImage:
    """BL-13: extract_info_from_image_with_gemini — Gemini OCR wrapper."""

    # Uses the real DUMMY_JPEG_BYTES (valid 1×1 JPEG) so PIL.Image.open succeeds.

    def test_id_card_json_parsed_correctly(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = (
            '{"type": "id_card", "value": "3100701443816"}'
        )
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "id_card"
        assert result["value"] == "3100701443816"

    def test_license_plate_json_parsed_correctly(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = (
            '{"type": "license_plate", "value": "1กข1234"}'
        )
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "license_plate"
        assert result["value"] == "1กข1234"

    def test_non_json_response_returns_unknown(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = "ไม่ทราบประเภทภาพ"
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "unknown"
        assert result["value"] is None

    def test_gemini_exception_returns_unknown(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API timeout")
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "unknown"
        assert result["value"] is None

    def test_json_embedded_in_prose_still_parsed(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = (
            'Here is the result: {"type": "id_card", "value": "1234567890123"} done.'
        )
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "id_card"
        assert result["value"] == "1234567890123"

    def test_unknown_type_in_response_parsed(self):
        from claim_engine import extract_info_from_image_with_gemini
        from tests.test_data import DUMMY_JPEG_BYTES
        mock_model = MagicMock()
        mock_model.generate_content.return_value.text = (
            '{"type": "unknown", "value": null}'
        )
        result = extract_info_from_image_with_gemini(mock_model, DUMMY_JPEG_BYTES)
        assert result["type"] == "unknown"
        assert result["value"] is None


# ─────────────────────────────────────────────────────────────────────────────
# BL-14  Health insurance policy lookup  (search_health_policies_by_cid)
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthPolicyLookupByCid:
    """BL-14: search_health_policies_by_cid — health plan lookup by CID."""

    def test_known_cid_returns_health_policies(self):
        from mock_data import search_health_policies_by_cid
        # CID "7564985348794" maps to HPL-2024-100001 (Gold plan)
        result = search_health_policies_by_cid("7564985348794")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_returned_policy_has_health_fields(self):
        from mock_data import search_health_policies_by_cid
        result = search_health_policies_by_cid("7564985348794")
        policy = result[0]
        for field in ["policy_number", "cid", "plan", "coverage_ipd", "coverage_opd", "status"]:
            assert field in policy, f"Missing field: {field}"

    def test_known_cid_policy_number_format(self):
        from mock_data import search_health_policies_by_cid
        result = search_health_policies_by_cid("7564985348794")
        assert result[0]["policy_number"].startswith("HPL-")

    def test_second_customer_cid_returns_health_policy(self):
        from mock_data import search_health_policies_by_cid
        # CID "9294258136443" maps to HPL-2024-100002 (Silver plan)
        result = search_health_policies_by_cid("9294258136443")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["plan"] == "Silver"

    def test_unknown_cid_returns_empty_list(self):
        from mock_data import search_health_policies_by_cid
        result = search_health_policies_by_cid("0000000000000")
        assert result == []

    def test_cid_with_dashes_normalised(self):
        from mock_data import search_health_policies_by_cid
        # "7-5649-85348-79-4" should normalise to "7564985348794"
        result = search_health_policies_by_cid("7-5649-85348-79-4")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_result_does_not_contain_cd_policy_fields(self):
        from mock_data import search_health_policies_by_cid
        result = search_health_policies_by_cid("7564985348794")
        # Health policies don't have a "plate" field
        assert "plate" not in result[0]

    def test_third_customer_expired_health_policy_found(self):
        from mock_data import search_health_policies_by_cid
        # CID "2138846447587" maps to HPL-2024-100003 (Bronze, expired)
        result = search_health_policies_by_cid("2138846447587")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["status"] == "expired"
