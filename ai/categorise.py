"""
ai/categorise.py — Classify a document image into one of the known categories.

Returns one of the strings defined in constants.VALID_CATEGORIES, or "unknown".
"""

import io
import logging
import re
from typing import Optional

from PIL import Image

from ai import call_ai
from constants import VALID_CATEGORIES

logger = logging.getLogger(__name__)

_VALID_STR = "\n".join(f"  - {c}" for c in sorted(VALID_CATEGORIES))

_PROMPT = f"""You are a document classifier for a Thai insurance claims system.
Examine this image and classify it into exactly ONE of the following categories:

{_VALID_STR}
  - unknown

Important Thai document hints:
- "รายการจดทะเบียน" (vehicle registration details) or any document showing เลขทะเบียน, ยี่ห้อรถ, เลขตัวรถ, สมุดคู่มือรถ → vehicle_registration
- "ใบอนุญาตขับขี่" or "ใบขับขี่" → driving_license
- "บัตรประจำตัวประชาชน" or Thai national ID card → citizen_id_card
- A photo showing car/vehicle damage (dents, scratches, broken parts) → vehicle_damage_photo
- A photo showing the accident scene or vehicle location → vehicle_location_photo
- "ใบรับรองแพทย์" → medical_certificate
- "ใบแจ้งค่ารักษา" or itemised hospital bill → itemised_bill
- "ใบเสร็จรับเงิน" → receipt
- "สรุปการรักษา" or discharge summary → discharge_summary

Return ONLY the category name — a single lowercase string with underscores, no spaces,
no markdown, no quotes, no punctuation.

Examples of correct output:
  driving_license
  vehicle_registration
  vehicle_damage_photo
  citizen_id_card
  unknown
"""


def categorise_document(image_bytes: bytes) -> str:
    """Classify a document image.

    Args:
        image_bytes: raw bytes of the uploaded image.

    Returns:
        Category string from VALID_CATEGORIES, or ``"unknown"``.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        raw = call_ai("categorise_document", _PROMPT, img)
        category = raw.strip().lower().split()[0] if raw.strip() else "unknown"
        # Strip any punctuation
        category = re.sub(r'[^a-z_]', '', category)
        if category not in VALID_CATEGORIES:
            logger.warning("AI returned unknown category '%s' — treating as unknown", category)
            return "unknown"
        logger.info("Document categorised as: %s", category)
        return category
    except Exception as exc:  # noqa: BLE001
        logger.error("Categorise error: %s", exc)
        return "unknown"
