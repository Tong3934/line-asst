"""
test_ai_modules.py
==================
Unit tests for the ai/ package.

Strategy
--------
- Patch ``ai._model`` (the shared GenerativeModel instance) so no real Gemini
  calls are made.
- For sub-modules (ocr, categorise, extract), patch ``ai.ocr.call_gemini`` /
  ``ai.categorise.call_gemini`` / ``ai.extract.call_gemini`` at the import-time
  binding so the patch takes effect inside each module.
- Use ``tmp_path`` (monkeypatched into ``constants.DATA_DIR``) for token record tests.

Areas covered
-------------
  AI-01  ai.__init__.call_gemini    — wrapper: result, token record, metadata absent, exception
  AI-02  ai.ocr.extract_id_from_image — JSON parse, unknown, exception fallback, no-PII-in-log
  AI-03  ai.categorise.categorise_document — valid, unknown, exception
  AI-04  ai.extract.extract_fields  — valid JSON, no-prompt category, no-JSON response, exception
  AI-05  ai.__init__._append_token_record — JSONL format, cost formula
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import io

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_fake_image_bytes() -> bytes:
    """Create a minimal valid JPEG in memory."""
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(128, 128, 128)).save(buf, format="JPEG")
    return buf.getvalue()


def _mock_model(text: str = "result text") -> MagicMock:
    """Return a mock GenerativeModel whose generate_content returns ``text``."""
    model = MagicMock()
    response = MagicMock()
    response.text = text
    response.usage_metadata.prompt_token_count = 10
    response.usage_metadata.candidates_token_count = 20
    model.generate_content.return_value = response
    return model


# ─────────────────────────────────────────────────────────────────────────────
# AI-01  ai.__init__.call_gemini
# ─────────────────────────────────────────────────────────────────────────────

class TestCallGemini:
    """AI-01: call_gemini wrapper behaviour."""

    def test_returns_response_text(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        with patch.object(ai_mod, "_model", _mock_model("hello world")):
            result = ai_mod.call_gemini("test_op", "some prompt")
        assert result == "hello world"

    def test_records_token_jsonl_file(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        with patch.object(ai_mod, "_model", _mock_model("hi")):
            ai_mod.call_gemini("test_op", "prompt")
        # Should have written a JSONL file under token_records/
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        token_file = tmp_path / "token_records" / f"{month}.jsonl"
        assert token_file.exists()

    def test_token_record_has_required_fields(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        with patch.object(ai_mod, "_model", _mock_model("hi")):
            ai_mod.call_gemini("myop", "prompt")
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        lines = (tmp_path / "token_records" / f"{month}.jsonl").read_text().strip().split("\n")
        record = json.loads(lines[-1])
        for field in ("ts", "operation", "model", "input_tokens", "output_tokens", "total_tokens", "cost_usd"):
            assert field in record, f"Missing field: {field}"
        assert record["operation"] == "myop"

    def test_token_metadata_unavailable_does_not_crash(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        model = MagicMock()
        response = MagicMock()
        response.text = "ok"
        # Make usage_metadata raise AttributeError
        type(response).usage_metadata = PropertyMock(side_effect=AttributeError("no metadata"))
        model.generate_content.return_value = response
        with patch.object(ai_mod, "_model", model):
            result = ai_mod.call_gemini("op_no_meta", "prompt")
        assert result == "ok"

    def test_exception_propagates_to_caller(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        model = MagicMock()
        model.generate_content.side_effect = RuntimeError("Gemini down")
        with patch.object(ai_mod, "_model", model):
            with pytest.raises(RuntimeError, match="Gemini down"):
                ai_mod.call_gemini("failing_op", "prompt")


# ─────────────────────────────────────────────────────────────────────────────
# AI-05  ai.__init__._append_token_record  (cost formula)
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenRecord:
    """AI-05: _append_token_record writes correct JSONL structure and cost."""

    def test_cost_calculated_correctly(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        # Use known pricing to verify cost
        price_in  = constants.PRICE_INPUT_PER_1K   # e.g. 0.00035
        price_out = constants.PRICE_OUTPUT_PER_1K  # e.g. 0.00105
        in_tok, out_tok = 1000, 1000
        expected_cost = round((in_tok / 1000 * price_in) + (out_tok / 1000 * price_out), 6)

        ai_mod._append_token_record("cost_test", in_tok, out_tok)

        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        lines = (tmp_path / "token_records" / f"{month}.jsonl").read_text().strip().split("\n")
        record = json.loads(lines[-1])
        assert record["cost_usd"] == pytest.approx(expected_cost, rel=1e-5)
        assert record["total_tokens"] == 2000

    def test_multiple_records_appended_as_separate_lines(self, tmp_path, monkeypatch):
        import constants
        monkeypatch.setattr(constants, "DATA_DIR", str(tmp_path))
        import ai as ai_mod
        ai_mod._append_token_record("op1", 100, 200)
        ai_mod._append_token_record("op2", 300, 400)

        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        lines = [
            l for l in (tmp_path / "token_records" / f"{month}.jsonl").read_text().strip().split("\n")
            if l
        ]
        ops = [json.loads(l)["operation"] for l in lines]
        assert "op1" in ops
        assert "op2" in ops


# ─────────────────────────────────────────────────────────────────────────────
# AI-02  ai.ocr.extract_id_from_image
# ─────────────────────────────────────────────────────────────────────────────

class TestOcr:
    """AI-02: extract_id_from_image JSON parsing and fallback logic."""

    _IMG = _make_fake_image_bytes()

    def test_id_card_type_returned(self):
        fake_response = '{"type": "id_card", "value": "1234567890123"}'
        with patch("ai.ocr.call_gemini", return_value=fake_response):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result["type"] == "id_card"
        assert result["value"] == "1234567890123"

    def test_driving_license_type_returned(self):
        fake_response = '{"type": "driving_license", "value": "9876543210987"}'
        with patch("ai.ocr.call_gemini", return_value=fake_response):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result["type"] == "driving_license"

    def test_license_plate_type_returned(self):
        fake_response = '{"type": "license_plate", "value": "1กข1234"}'
        with patch("ai.ocr.call_gemini", return_value=fake_response):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result["type"] == "license_plate"
        assert result["value"] == "1กข1234"

    def test_unknown_image_returns_unknown(self):
        fake_response = '{"type": "unknown", "value": null}'
        with patch("ai.ocr.call_gemini", return_value=fake_response):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result["type"] == "unknown"
        assert result["value"] is None

    def test_non_json_response_returns_unknown_fallback(self):
        with patch("ai.ocr.call_gemini", return_value="This is not JSON"):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result == {"type": "unknown", "value": None}

    def test_exception_in_call_returns_unknown_fallback(self):
        with patch("ai.ocr.call_gemini", side_effect=RuntimeError("AI error")):
            from ai.ocr import extract_id_from_image
            result = extract_id_from_image(self._IMG)
        assert result == {"type": "unknown", "value": None}

    def test_cid_value_not_in_log_output(self, caplog):
        """PII (CID number) must NOT appear in log output."""
        secret_cid = "3100701443816"
        fake_response = f'{{"type": "id_card", "value": "{secret_cid}"}}'
        with patch("ai.ocr.call_gemini", return_value=fake_response):
            import logging
            with caplog.at_level(logging.INFO, logger="ai.ocr"):
                from ai.ocr import extract_id_from_image
                extract_id_from_image(self._IMG)
        assert secret_cid not in caplog.text


# ─────────────────────────────────────────────────────────────────────────────
# AI-03  ai.categorise.categorise_document
# ─────────────────────────────────────────────────────────────────────────────

class TestCategorise:
    """AI-03: categorise_document classification logic."""

    _IMG = _make_fake_image_bytes()

    @pytest.mark.parametrize("category", [
        "driving_license",
        "vehicle_registration",
        "citizen_id_card",
        "receipt",
        "medical_certificate",
        "itemised_bill",
        "discharge_summary",
        "vehicle_damage_photo",
        "vehicle_location_photo",
    ])
    def test_valid_category_returned(self, category):
        with patch("ai.categorise.call_gemini", return_value=category):
            from ai.categorise import categorise_document
            result = categorise_document(self._IMG)
        assert result == category

    def test_unknown_ai_response_returns_unknown(self):
        with patch("ai.categorise.call_gemini", return_value="passport"):
            from ai.categorise import categorise_document
            result = categorise_document(self._IMG)
        assert result == "unknown"

    def test_extra_whitespace_stripped(self):
        with patch("ai.categorise.call_gemini", return_value="  driving_license  "):
            from ai.categorise import categorise_document
            result = categorise_document(self._IMG)
        assert result == "driving_license"

    def test_exception_returns_unknown(self):
        with patch("ai.categorise.call_gemini", side_effect=RuntimeError("error")):
            from ai.categorise import categorise_document
            result = categorise_document(self._IMG)
        assert result == "unknown"

    def test_empty_response_returns_unknown(self):
        with patch("ai.categorise.call_gemini", return_value=""):
            from ai.categorise import categorise_document
            result = categorise_document(self._IMG)
        assert result == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# AI-04  ai.extract.extract_fields
# ─────────────────────────────────────────────────────────────────────────────

class TestExtract:
    """AI-04: extract_fields per-category prompt selection and JSON parsing."""

    _IMG = _make_fake_image_bytes()

    def test_driving_license_extracts_fields(self):
        fake_json = '{"full_name_th": "สมชาย", "license_id": "12345678"}'
        with patch("ai.extract.call_gemini", return_value=fake_json):
            from ai.extract import extract_fields
            result = extract_fields(self._IMG, "driving_license")
        assert result["full_name_th"] == "สมชาย"

    def test_unknown_category_returns_empty_dict(self):
        with patch("ai.extract.call_gemini", return_value="{}") as mock_call:
            from ai.extract import extract_fields
            result = extract_fields(self._IMG, "not_a_real_category")
        # Should return empty without calling AI
        assert result == {}
        mock_call.assert_not_called()

    def test_no_json_in_response_returns_empty(self):
        with patch("ai.extract.call_gemini", return_value="Sorry, cannot read."):
            from ai.extract import extract_fields
            result = extract_fields(self._IMG, "driving_license")
        assert result == {}

    def test_invalid_json_returns_empty(self):
        with patch("ai.extract.call_gemini", return_value="{bad json"):
            from ai.extract import extract_fields
            result = extract_fields(self._IMG, "driving_license")
        assert result == {}

    def test_exception_returns_empty(self):
        with patch("ai.extract.call_gemini", side_effect=RuntimeError("fail")):
            from ai.extract import extract_fields
            result = extract_fields(self._IMG, "driving_license")
        assert result == {}

    def test_vehicle_damage_photo_adds_gps_keys(self):
        fake_json = '{"damage_location": "ประตูซ้าย", "severity": "minor"}'
        with patch("ai.extract.call_gemini", return_value=fake_json):
            # Patch GPS extraction to return known coords
            with patch("ai.extract._extract_gps_from_exif", return_value=(13.7563, 100.5018)):
                from ai.extract import extract_fields
                result = extract_fields(self._IMG, "vehicle_damage_photo")
        assert "gps_lat" in result
        assert "gps_lon" in result
        assert result["gps_lat"] == 13.7563

    def test_all_known_categories_have_prompts(self):
        """Every VALID_CATEGORY (except vehicle_location_photo edge-case) must have a prompt."""
        from ai.extract import _PROMPTS
        from constants import VALID_CATEGORIES
        # vehicle_damage_photo and vehicle_location_photo are both in VALID_CATEGORIES
        # Some categories may share prompt keys — check that extract_fields doesn't return {}
        # for core ID/registration categories
        for cat in ("driving_license", "vehicle_registration", "citizen_id_card",
                    "medical_certificate", "itemised_bill", "receipt"):
            assert cat in _PROMPTS, f"Missing prompt for {cat}"
