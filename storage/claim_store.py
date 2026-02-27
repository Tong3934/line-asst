"""
storage/claim_store.py — Read/write claim metadata (status.yaml) and
                          extracted AI data (extracted_data.json).

All paths are rooted at {DATA_DIR}/claims/{claim_id}/.

12-Factor: no credentials here; DATA_DIR injected via environment.
"""

import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import yaml

from constants import DATA_DIR

logger = logging.getLogger(__name__)

# ── Path helpers ──────────────────────────────────────────────────────────────

def _claim_dir(claim_id: str) -> pathlib.Path:
    return pathlib.Path(DATA_DIR) / "claims" / claim_id


def _status_path(claim_id: str) -> pathlib.Path:
    return _claim_dir(claim_id) / "status.yaml"


def _extracted_path(claim_id: str) -> pathlib.Path:
    return _claim_dir(claim_id) / "extracted_data.json"


def _summary_path(claim_id: str) -> pathlib.Path:
    return _claim_dir(claim_id) / "summary.md"


# ── Public API ────────────────────────────────────────────────────────────────

def create_claim(
    claim_id: str,
    claim_type: str,
    line_user_id: str,
    has_counterpart: Optional[str] = None,
) -> None:
    """Create claim folder, empty extracted_data.json, and initial status.yaml."""
    d = _claim_dir(claim_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "documents").mkdir(exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    status = {
        "claim_id": claim_id,
        "claim_type": claim_type,
        "line_user_id": line_user_id,
        "has_counterpart": has_counterpart,
        "status": "Draft",
        "memo": "",
        "created_at": now,
        "submitted_at": None,
        "documents": [],
        "metrics": {
            "response_times_ms": [],
            "total_paid_amount": None,
        },
    }
    _status_path(claim_id).write_text(yaml.dump(status, allow_unicode=True))
    _extracted_path(claim_id).write_text(json.dumps({}, ensure_ascii=False, indent=2))
    logger.info("Created claim %s (type=%s)", claim_id, claim_type)


def get_claim_status(claim_id: str) -> Dict:
    """Read and return status.yaml as dict. Returns empty dict if not found."""
    p = _status_path(claim_id)
    if not p.exists():
        logger.warning("status.yaml not found for %s", claim_id)
        return {}
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def update_claim_status(
    claim_id: str,
    status: str,
    memo: Optional[str] = None,
    paid_amount: Optional[float] = None,
    submitted_at: Optional[str] = None,
) -> None:
    """Update status (and optionally memo / paid_amount) in status.yaml."""
    data = get_claim_status(claim_id)
    if not data:
        logger.error("Cannot update status — claim %s not found", claim_id)
        return

    data["status"] = status
    if memo is not None:
        data["memo"] = memo
    if paid_amount is not None:
        data.setdefault("metrics", {})["total_paid_amount"] = paid_amount
    if submitted_at is not None:
        data["submitted_at"] = submitted_at

    _status_path(claim_id).write_text(yaml.dump(data, allow_unicode=True))
    logger.info("Updated claim %s status → %s", claim_id, status)


def mark_document_useful(claim_id: str, filename: str, useful: bool) -> None:
    """Set useful flag on one document entry in status.yaml."""
    data = get_claim_status(claim_id)
    for doc in data.get("documents", []):
        if doc.get("filename") == filename:
            doc["useful"] = useful
            break
    _status_path(claim_id).write_text(yaml.dump(data, allow_unicode=True))
    logger.info("Claim %s doc %s marked useful=%s", claim_id, filename, useful)


def add_document_to_claim(claim_id: str, category: str, filename: str) -> None:
    """Append a document entry (useful=null) to status.yaml documents list."""
    data = get_claim_status(claim_id)
    data.setdefault("documents", []).append({
        "category": category,
        "filename": filename,
        "useful": None,
    })
    _status_path(claim_id).write_text(yaml.dump(data, allow_unicode=True))


def update_extracted_data(claim_id: str, category: str, fields: Dict) -> None:
    """Merge fields into extracted_data.json under category key.

    List-type categories (damage_photos, medical_receipts) are appended;
    all others replace the existing key.
    """
    p = _extracted_path(claim_id)
    existing: Dict = {}
    if p.exists():
        try:
            existing = json.loads(p.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            logger.warning("Corrupted extracted_data.json for %s — resetting", claim_id)

    list_categories = {"damage_photos", "medical_receipts"}
    if category in list_categories:
        existing.setdefault(category, [])
        existing[category].append(fields)
    else:
        existing[category] = fields

    p.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    logger.debug("Updated extracted_data for claim %s category %s", claim_id, category)


def get_extracted_data(claim_id: str) -> Dict:
    """Return full extracted_data.json as dict."""
    p = _extracted_path(claim_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        logger.warning("Corrupted extracted_data.json for %s", claim_id)
        return {}


def save_summary(claim_id: str, markdown_text: str) -> None:
    """Write AI-generated summary.md for the claim."""
    _summary_path(claim_id).write_text(markdown_text, encoding="utf-8")


def add_response_time(claim_id: str, ms: int) -> None:
    """Append a response-time measurement (ms) to status.yaml metrics."""
    data = get_claim_status(claim_id)
    data.setdefault("metrics", {}).setdefault("response_times_ms", []).append(ms)
    _status_path(claim_id).write_text(yaml.dump(data, allow_unicode=True))


def list_all_claims(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict]:
    """Scan all claim folders and return list of status.yaml contents.

    Args:
        status_filter: e.g. "Submitted" — returns only matching claims
        type_filter:   "CD" or "H"
        date_from:     "YYYY-MM-DD" inclusive
        date_to:       "YYYY-MM-DD" inclusive
    """
    claims_root = pathlib.Path(DATA_DIR) / "claims"
    if not claims_root.exists():
        return []

    results: List[Dict] = []
    for folder in sorted(claims_root.iterdir()):
        if not folder.is_dir():
            continue
        sy = folder / "status.yaml"
        if not sy.exists():
            continue
        try:
            data = yaml.safe_load(sy.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue

        if status_filter and data.get("status") != status_filter:
            continue
        if type_filter and data.get("claim_type") != type_filter:
            continue

        created = (data.get("created_at") or "")[:10]
        if date_from and created < date_from:
            continue
        if date_to and created > date_to:
            continue

        results.append(data)

    return results
