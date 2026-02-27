"""
storage/document_store.py — Save and retrieve document image files.

All images are stored at: {DATA_DIR}/claims/{claim_id}/documents/{filename}

Filename convention:  {category}_{YYYYMMDD_HHMMSS}.{ext}
"""

import logging
import pathlib
from datetime import datetime, timezone
from typing import Optional

from constants import DATA_DIR

logger = logging.getLogger(__name__)


def _docs_dir(claim_id: str) -> pathlib.Path:
    return pathlib.Path(DATA_DIR) / "claims" / claim_id / "documents"


def save_document(
    claim_id: str,
    category: str,
    image_bytes: bytes,
    ext: str = "jpg",
    index: Optional[int] = None,
) -> str:
    """Save image bytes to the claim's documents folder.

    Args:
        claim_id:    e.g. "CD-20260226-000001"
        category:    document category string
        image_bytes: raw image bytes
        ext:         file extension without dot (jpg, png, webp …)
        index:       optional numeric suffix for list-type docs (damage photos)

    Returns:
        Filename only (not full path), e.g.
        ``vehicle_damage_photo_1_20260226_120030.jpg``
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    idx_part = f"_{index}" if index is not None else ""
    filename = f"{category}{idx_part}_{ts}.{ext}"

    target = _docs_dir(claim_id) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(image_bytes)
    logger.info("Saved document %s for claim %s (%d bytes)", filename, claim_id, len(image_bytes))
    return filename


def get_document_bytes(claim_id: str, filename: str) -> bytes:
    """Read and return raw bytes of a stored document.

    Raises:
        FileNotFoundError: if the document does not exist.
    """
    path = _docs_dir(claim_id) / filename
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")
    return path.read_bytes()


def get_document_path(claim_id: str, filename: str) -> str:
    """Return absolute path string to a document file."""
    return str(_docs_dir(claim_id) / filename)


def list_documents(claim_id: str) -> list[str]:
    """Return sorted list of filenames in the claim's documents folder."""
    d = _docs_dir(claim_id)
    if not d.exists():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file())
