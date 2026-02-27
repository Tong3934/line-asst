"""
test_storage.py
===============
Unit tests for the storage layer: claim_store.py and document_store.py.

Strategy
--------
- Use pytest ``tmp_path`` fixture — every test gets its own temp directory.
- Set ``DATA_DIR`` to ``tmp_path`` via monkeypatching the ``constants`` module so
  all path helpers under test resolve inside the temp tree.
- No HTTP server, no mocks — these are direct function calls against the real
  file-system implementation.

Areas covered
-------------
  ST-01  claim_store  — create_claim, get_claim_status, update_claim_status,
                        add_document_to_claim, mark_document_useful,
                        update_extracted_data, get_extracted_data,
                        save_summary, add_response_time, list_all_claims (with filters)
  ST-02  document_store — save_document, get_document_bytes,
                          get_document_path, list_documents
"""

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Redirect DATA_DIR to tmp_path for every test that uses this fixture."""
    monkeypatch.setattr("constants.DATA_DIR", str(tmp_path))
    # Also patch the imported references inside the storage modules
    import storage.claim_store as cs
    import storage.document_store as ds
    monkeypatch.setattr(cs, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ds, "DATA_DIR", str(tmp_path))
    return tmp_path


_CLAIM_ID = "CD-20260226-000001"
_CLAIM_TYPE = "CD"
_USER_ID = "Udeadbeef000000000000000000000001"


# ─────────────────────────────────────────────────────────────────────────────
# ST-01  storage/claim_store.py
# ─────────────────────────────────────────────────────────────────────────────

class TestClaimStore:
    """ST-01: claim_store CRUD operations."""

    def _import(self):
        """Import after fixture has patched DATA_DIR."""
        import storage.claim_store as cs
        return cs

    # ── create_claim ────────────────────────────────────────────────────────

    def test_create_claim_creates_directory(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        assert (data_dir / "claims" / _CLAIM_ID).is_dir()

    def test_create_claim_creates_documents_subdir(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        assert (data_dir / "claims" / _CLAIM_ID / "documents").is_dir()

    def test_create_claim_writes_status_yaml(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        assert (data_dir / "claims" / _CLAIM_ID / "status.yaml").is_file()

    def test_create_claim_writes_extracted_data_json(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        p = data_dir / "claims" / _CLAIM_ID / "extracted_data.json"
        assert p.is_file()
        assert json.loads(p.read_text()) == {}

    def test_create_claim_initial_status_is_draft(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["status"] == "Draft"

    def test_create_claim_records_claim_type(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["claim_type"] == _CLAIM_TYPE

    def test_create_claim_records_user_id(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["line_user_id"] == _USER_ID

    def test_create_claim_with_counterpart(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID, has_counterpart="มีคู่กรณี")
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["has_counterpart"] == "มีคู่กรณี"

    # ── get_claim_status ─────────────────────────────────────────────────────

    def test_get_claim_status_nonexistent_returns_empty_dict(self, data_dir):
        cs = self._import()
        result = cs.get_claim_status("nonexistent-claim-id")
        assert result == {}

    def test_get_claim_status_returns_dict(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        result = cs.get_claim_status(_CLAIM_ID)
        assert isinstance(result, dict)
        assert "claim_id" in result

    # ── update_claim_status ──────────────────────────────────────────────────

    def test_update_claim_status_changes_status_field(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_claim_status(_CLAIM_ID, status="UnderReview")
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["status"] == "UnderReview"

    def test_update_claim_status_sets_memo(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_claim_status(_CLAIM_ID, status="UnderReview", memo="Looks good")
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["memo"] == "Looks good"

    def test_update_claim_status_sets_submitted_at(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_claim_status(_CLAIM_ID, status="Submitted", submitted_at="2026-02-26T00:00:00+00:00")
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["submitted_at"] == "2026-02-26T00:00:00+00:00"

    def test_update_claim_status_sets_paid_amount(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_claim_status(_CLAIM_ID, status="Approved", paid_amount=15000.0)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["metrics"]["total_paid_amount"] == 15000.0

    def test_update_claim_status_missing_claim_does_nothing(self, data_dir):
        cs = self._import()
        # Should log error and return without crashing
        cs.update_claim_status("no-such-claim", status="Weird")

    # ── add_document_to_claim ────────────────────────────────────────────────

    def test_add_document_to_claim_appends_to_documents_list(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_document_to_claim(_CLAIM_ID, category="driving_license", filename="driving_license_001.jpg")
        data = cs.get_claim_status(_CLAIM_ID)
        assert len(data["documents"]) == 1
        assert data["documents"][0]["category"] == "driving_license"

    def test_add_document_to_claim_multiple_documents(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_document_to_claim(_CLAIM_ID, category="driving_license", filename="a.jpg")
        cs.add_document_to_claim(_CLAIM_ID, category="vehicle_registration", filename="b.jpg")
        data = cs.get_claim_status(_CLAIM_ID)
        assert len(data["documents"]) == 2

    def test_add_document_useful_is_none_by_default(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_document_to_claim(_CLAIM_ID, category="driving_license", filename="a.jpg")
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["documents"][0]["useful"] is None

    # ── mark_document_useful ─────────────────────────────────────────────────

    def test_mark_document_useful_sets_true(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_document_to_claim(_CLAIM_ID, category="driving_license", filename="a.jpg")
        cs.mark_document_useful(_CLAIM_ID, filename="a.jpg", useful=True)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["documents"][0]["useful"] is True

    def test_mark_document_useful_sets_false(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_document_to_claim(_CLAIM_ID, category="driving_license", filename="a.jpg")
        cs.mark_document_useful(_CLAIM_ID, filename="a.jpg", useful=False)
        data = cs.get_claim_status(_CLAIM_ID)
        assert data["documents"][0]["useful"] is False

    # ── update_extracted_data ────────────────────────────────────────────────

    def test_update_extracted_data_stores_category(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_extracted_data(_CLAIM_ID, "driving_license", {"name": "สมชาย"})
        result = cs.get_extracted_data(_CLAIM_ID)
        assert result["driving_license"]["name"] == "สมชาย"

    def test_update_extracted_data_non_list_category_replaces(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_extracted_data(_CLAIM_ID, "driving_license", {"name": "ก"})
        cs.update_extracted_data(_CLAIM_ID, "driving_license", {"name": "ข"})
        result = cs.get_extracted_data(_CLAIM_ID)
        assert result["driving_license"]["name"] == "ข"

    def test_update_extracted_data_list_category_appends(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_extracted_data(_CLAIM_ID, "damage_photos", {"severity": "minor"})
        cs.update_extracted_data(_CLAIM_ID, "damage_photos", {"severity": "moderate"})
        result = cs.get_extracted_data(_CLAIM_ID)
        assert isinstance(result["damage_photos"], list)
        assert len(result["damage_photos"]) == 2

    def test_update_extracted_data_medical_receipts_appends(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.update_extracted_data(_CLAIM_ID, "medical_receipts", {"total": 1000})
        cs.update_extracted_data(_CLAIM_ID, "medical_receipts", {"total": 500})
        result = cs.get_extracted_data(_CLAIM_ID)
        assert len(result["medical_receipts"]) == 2

    # ── get_extracted_data ───────────────────────────────────────────────────

    def test_get_extracted_data_nonexistent_returns_empty(self, data_dir):
        cs = self._import()
        result = cs.get_extracted_data("nonexistent-claim")
        assert result == {}

    def test_get_extracted_data_returns_dict(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        result = cs.get_extracted_data(_CLAIM_ID)
        assert isinstance(result, dict)

    # ── save_summary ─────────────────────────────────────────────────────────

    def test_save_summary_writes_file(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.save_summary(_CLAIM_ID, "# Claim Summary\nTest content")
        p = data_dir / "claims" / _CLAIM_ID / "summary.md"
        assert p.is_file()
        assert "Claim Summary" in p.read_text()

    # ── add_response_time ────────────────────────────────────────────────────

    def test_add_response_time_appends_ms(self, data_dir):
        cs = self._import()
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        cs.add_response_time(_CLAIM_ID, ms=1200)
        cs.add_response_time(_CLAIM_ID, ms=850)
        data = cs.get_claim_status(_CLAIM_ID)
        assert 1200 in data["metrics"]["response_times_ms"]
        assert 850 in data["metrics"]["response_times_ms"]

    # ── list_all_claims ──────────────────────────────────────────────────────

    def test_list_all_claims_returns_all(self, data_dir):
        cs = self._import()
        cs.create_claim("CD-20260226-000001", "CD", _USER_ID)
        cs.create_claim("H-20260226-000001", "H", _USER_ID)
        result = cs.list_all_claims()
        assert len(result) == 2

    def test_list_all_claims_empty_dir_returns_empty(self, data_dir):
        cs = self._import()
        result = cs.list_all_claims()
        assert result == []

    def test_list_all_claims_filter_by_status(self, data_dir):
        cs = self._import()
        cs.create_claim("CD-20260226-000001", "CD", _USER_ID)
        cs.create_claim("CD-20260226-000002", "CD", _USER_ID)
        cs.update_claim_status("CD-20260226-000001", status="Submitted")
        result = cs.list_all_claims(status_filter="Submitted")
        assert len(result) == 1
        assert result[0]["claim_id"] == "CD-20260226-000001"

    def test_list_all_claims_filter_by_type(self, data_dir):
        cs = self._import()
        cs.create_claim("CD-20260226-000001", "CD", _USER_ID)
        cs.create_claim("H-20260226-000001", "H", _USER_ID)
        result = cs.list_all_claims(type_filter="H")
        assert len(result) == 1
        assert result[0]["claim_type"] == "H"

    def test_list_all_claims_filter_combined(self, data_dir):
        cs = self._import()
        cs.create_claim("CD-20260226-000001", "CD", _USER_ID)
        cs.create_claim("H-20260226-000001", "H", _USER_ID)
        cs.update_claim_status("CD-20260226-000001", status="Submitted")
        result = cs.list_all_claims(status_filter="Submitted", type_filter="CD")
        assert len(result) == 1

    def test_list_all_claims_nonexistent_claims_dir_returns_empty(self, tmp_path, monkeypatch):
        """If the claims directory does not exist at all, return empty list."""
        import storage.claim_store as cs
        monkeypatch.setattr(cs, "DATA_DIR", str(tmp_path / "nonexistent"))
        result = cs.list_all_claims()
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# ST-02  storage/document_store.py
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentStore:
    """ST-02: document_store file-level operations."""

    _BYTES = b"\xff\xd8\xff\xe0fake_jpeg_content"

    def _import(self):
        import storage.document_store as ds
        return ds

    # ── save_document ────────────────────────────────────────────────────────

    def test_save_document_creates_file(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        p = data_dir / "claims" / _CLAIM_ID / "documents" / filename
        assert p.is_file()

    def test_save_document_returns_filename_string(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        assert isinstance(filename, str)
        assert filename.endswith(".jpg")

    def test_save_document_filename_contains_category(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        assert "driving_license" in filename

    def test_save_document_with_index_in_filename(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "vehicle_damage_photo", self._BYTES, index=2)
        assert "_2_" in filename

    def test_save_document_without_index_no_underscore_number(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        # Category immediately followed by underscore then timestamp: no index part
        parts = filename.replace("driving_license_", "", 1)
        assert not parts.startswith("_")

    def test_save_document_content_written_correctly(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        p = data_dir / "claims" / _CLAIM_ID / "documents" / filename
        assert p.read_bytes() == self._BYTES

    def test_save_document_custom_extension(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES, ext="png")
        assert filename.endswith(".png")

    # ── get_document_bytes ───────────────────────────────────────────────────

    def test_get_document_bytes_returns_original_bytes(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        result = ds.get_document_bytes(_CLAIM_ID, filename)
        assert result == self._BYTES

    def test_get_document_bytes_missing_raises_filenotfounderror(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        with pytest.raises(FileNotFoundError):
            ds.get_document_bytes(_CLAIM_ID, "nonexistent.jpg")

    # ── get_document_path ────────────────────────────────────────────────────

    def test_get_document_path_returns_string(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        path_str = ds.get_document_path(_CLAIM_ID, filename)
        assert isinstance(path_str, str)
        assert filename in path_str

    def test_get_document_path_is_absolute(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        filename = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        path_str = ds.get_document_path(_CLAIM_ID, filename)
        assert Path(path_str).is_absolute()

    # ── list_documents ───────────────────────────────────────────────────────

    def test_list_documents_returns_sorted_filenames(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        import time
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        f1 = ds.save_document(_CLAIM_ID, "driving_license", self._BYTES)
        time.sleep(0.01)  # Ensure distinct timestamps
        f2 = ds.save_document(_CLAIM_ID, "vehicle_registration", self._BYTES)
        result = ds.list_documents(_CLAIM_ID)
        assert sorted(result) == result
        assert f1 in result
        assert f2 in result

    def test_list_documents_empty_returns_empty_list(self, data_dir):
        ds = self._import()
        import storage.claim_store as cs
        cs.create_claim(_CLAIM_ID, _CLAIM_TYPE, _USER_ID)
        result = ds.list_documents(_CLAIM_ID)
        assert result == []

    def test_list_documents_nonexistent_claim_returns_empty(self, data_dir):
        ds = self._import()
        result = ds.list_documents("no-such-claim")
        assert result == []
