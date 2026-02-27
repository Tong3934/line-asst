"""
ai/ocr.py — Extract identity information from an ID card or driving license photo.

Returns a dict: {"type": "id_card"|"license_plate"|"unknown", "value": str|None}

Security: no PII (national IDs, names) is written to logs.
"""

import io
import json
import logging
import re
from typing import Dict

from PIL import Image

from ai import call_gemini

logger = logging.getLogger(__name__)

_PROMPT = """Analyse this image. Determine if it is a Thai national ID card or a Thai vehicle
registration plate / driving license.

Return ONLY valid JSON in this exact format — no markdown, no prose:
{
  "type": "id_card" | "driving_license" | "license_plate" | "unknown",
  "value": "<13-digit national ID number OR license plate text OR null>"
}

Rules:
1. If this is a national ID card → extract the 13-digit ID number (digits only, no dashes or spaces).
2. If this is a driving license → extract the 13-digit citizen ID embedded in it (digits only).
3. If this is a vehicle registration → extract the plate characters (e.g. "1กข1234"), no province.
4. If the image is unclear or none of the above → type = "unknown", value = null.
5. Never mask digits with asterisks (*). Return ALL digits.
"""


def extract_id_from_image(image_bytes: bytes) -> Dict:
    """Use Gemini to read an ID card or driving license photo.

    Args:
        image_bytes: raw bytes of the uploaded image.

    Returns:
        ``{"type": "id_card"|"driving_license"|"license_plate"|"unknown", "value": str|None}``
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        raw = call_gemini("ocr_id_image", _PROMPT, img)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            logger.info("OCR type=%s (value masked in log)", result.get("type"))
            return result
        logger.warning("OCR response did not contain JSON: %s", raw[:100])
    except Exception as exc:  # noqa: BLE001
        logger.error("OCR error: %s", exc)
    return {"type": "unknown", "value": None}
