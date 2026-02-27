"""
storage/sequence.py — Claim ID sequence generator.

Thread-safe, file-backed counter that survives container restarts.
Uses threading.Lock() + fcntl.flock for dual in-process / inter-process safety.

12-Factor: sequence.json lives on the /data volume (backing service).
"""

import fcntl
import json
import threading
import datetime
import pathlib
import logging

from constants import DATA_DIR

logger = logging.getLogger(__name__)

_SEQUENCE_PATH = pathlib.Path(DATA_DIR) / "sequence.json"
_lock = threading.Lock()


def _ensure_sequence_file() -> None:
    """Create sequence.json with zero counters if it doesn't exist."""
    if not _SEQUENCE_PATH.exists():
        _SEQUENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _SEQUENCE_PATH.write_text(json.dumps({"CD": 0, "H": 0}))
        logger.info("Created sequence.json at %s", _SEQUENCE_PATH)


def next_claim_id(claim_type: str) -> str:
    """Atomically increment counter for claim_type and return formatted Claim ID.

    Format: ``{type}-{YYYYMMDD}-{counter:06d}``
    Example: ``CD-20260226-000013``

    Args:
        claim_type: "CD" or "H"

    Returns:
        Formatted Claim ID string.
    """
    _ensure_sequence_file()
    with _lock:
        with open(_SEQUENCE_PATH, "r+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            data = json.load(fh)
            data[claim_type] = data.get(claim_type, 0) + 1
            fh.seek(0)
            json.dump(data, fh)
            fh.truncate()
            counter = data[claim_type]

    today = datetime.date.today().strftime("%Y%m%d")
    claim_id = f"{claim_type}-{today}-{counter:06d}"
    logger.info("Generated Claim ID: %s", claim_id)
    return claim_id
