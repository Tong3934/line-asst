"""
ai/extract.py — Extract structured JSON fields from a classified document image.

Each document category has its own prompt.  All prompts share:
  - Buddhist Era → Gregorian date conversion (subtract 543)
  - null for unreadable fields (never guess)
  - GPS from EXIF (parsed in Python before the AI call)
  - JSON only — no markdown, no prose

Security: no PII written to logs.
"""

import io
import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from PIL import Image, ExifTags

from ai import call_gemini

logger = logging.getLogger(__name__)

# ── GPS EXIF helpers ──────────────────────────────────────────────────────────

def _dms_to_decimal(degrees: float, minutes: float, seconds: float, direction: str) -> float:
    decimal = degrees + minutes / 60 + seconds / 3600
    if direction in ("S", "W"):
        decimal = -decimal
    return round(decimal, 7)


def _extract_gps_from_exif(image_bytes: bytes) -> Tuple[Optional[float], Optional[float]]:
    """Extract GPS latitude and longitude from image EXIF data."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        exif_data = img._getexif()
        if not exif_data:
            return None, None

        gps_tag = next(
            (tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"), None
        )
        if not gps_tag or gps_tag not in exif_data:
            return None, None

        gps_info = exif_data[gps_tag]
        gps_keys = {v: k for k, v in ExifTags.GPSTAGS.items()}

        lat_data  = gps_info.get(gps_keys.get("GPSLatitude"))
        lat_ref   = gps_info.get(gps_keys.get("GPSLatitudeRef"), "N")
        lon_data  = gps_info.get(gps_keys.get("GPSLongitude"))
        lon_ref   = gps_info.get(gps_keys.get("GPSLongitudeRef"), "E")

        if lat_data and lon_data:
            lat = _dms_to_decimal(float(lat_data[0]), float(lat_data[1]), float(lat_data[2]), lat_ref)
            lon = _dms_to_decimal(float(lon_data[0]), float(lon_data[1]), float(lon_data[2]), lon_ref)
            return lat, lon
    except Exception:  # noqa: BLE001
        pass
    return None, None


# ── Per-category prompt templates ─────────────────────────────────────────────

_COMMON_RULES = """
Rules:
- Thai documents use Buddhist Era (พ.ศ.) — convert ALL dates to Gregorian by subtracting 543.
  Example: พ.ศ. 2563 → 2020. Return all dates as YYYY-MM-DD.
- If a field cannot be read clearly, return null. NEVER guess or fabricate values.
- Return ONLY valid JSON. No markdown code fences, no prose, no explanation.
"""

_PROMPTS: Dict[str, str] = {
    "driving_license": f"""Extract fields from this Thai driving license image.
Return JSON only:
{{
  "full_name_th": "<Thai full name or null>",
  "full_name_en": "<English full name or null>",
  "license_id": "<8-digit license number or null>",
  "citizen_id": "<13-digit citizen ID or null>",
  "date_of_birth": "<YYYY-MM-DD or null>",
  "issue_date": "<YYYY-MM-DD or null>",
  "expiry_date": "<YYYY-MM-DD or null>"
}}
{_COMMON_RULES}""",

    "vehicle_registration": f"""Extract fields from this Thai vehicle registration document.
Return JSON only:
{{
  "plate": "<license plate text or null>",
  "province": "<province name in Thai or null>",
  "vehicle_type": "<vehicle type in Thai or null>",
  "brand": "<manufacturer brand or null>",
  "chassis_number": "<17-character VIN / chassis number or null>",
  "engine_number": "<engine number or null>",
  "model_year": "<4-digit year or null>"
}}
{_COMMON_RULES}""",

    "citizen_id_card": f"""Extract fields from this Thai national ID card.
Return JSON only:
{{
  "full_name_th": "<Thai full name or null>",
  "full_name_en": "<English full name or null>",
  "citizen_id": "<13-digit citizen ID or null>",
  "date_of_birth": "<YYYY-MM-DD or null>",
  "issue_date": "<YYYY-MM-DD or null>",
  "expiry_date": "<YYYY-MM-DD or null>"
}}
{_COMMON_RULES}""",

    "medical_certificate": f"""Extract fields from this medical certificate.
Return JSON only:
{{
  "patient_name": "<patient full name or null>",
  "diagnosis": "<diagnosis description or null>",
  "treatment": "<treatment description or null>",
  "doctor_name": "<doctor full name or null>",
  "hospital": "<hospital name or null>",
  "date": "<YYYY-MM-DD or null>"
}}
{_COMMON_RULES}""",

    "itemised_bill": f"""Extract fields from this itemised medical bill.
Return JSON only:
{{
  "line_items": [
    {{"description": "<item description>", "amount": <numeric THB>}}
  ],
  "total": <numeric THB total or null>
}}
{_COMMON_RULES}""",

    "discharge_summary": f"""Extract fields from this hospital discharge summary.
Return JSON only:
{{
  "diagnosis": "<primary diagnosis or null>",
  "treatment": "<treatment summary or null>",
  "admission_date": "<YYYY-MM-DD or null>",
  "discharge_date": "<YYYY-MM-DD or null>"
}}
{_COMMON_RULES}""",

    "receipt": f"""Extract fields from this medical receipt / payment receipt.
Return JSON only:
{{
  "hospital_name": "<hospital or clinic name or null>",
  "billing_number": "<billing/receipt number or null>",
  "total_paid": <numeric THB or null>,
  "date": "<YYYY-MM-DD or null>",
  "items": [
    {{"description": "<item description>", "amount": <numeric THB>}}
  ]
}}
{_COMMON_RULES}""",

    "vehicle_damage_photo": f"""Analyse this vehicle damage photo.
GPS coordinates will be provided separately in the JSON (extracted from EXIF).
Return JSON only:
{{
  "damage_location": "<location on vehicle e.g. ประตูซ้ายหน้า or null>",
  "damage_description": "<description of damage in Thai or null>",
  "severity": "minor" | "moderate" | "severe" | null
}}
{_COMMON_RULES}""",

    "vehicle_location_photo": f"""Analyse this vehicle location photo.
GPS coordinates will be provided separately in the JSON (extracted from EXIF).
Return JSON only:
{{
  "location_description": "<road/area description in Thai or null>",
  "road_conditions": "<road condition e.g. แห้ง, เปียก or null>",
  "weather_conditions": "<weather e.g. แดด, ฝนตก, เมฆมาก or null>"
}}
{_COMMON_RULES}""",
}


# ── Public API ────────────────────────────────────────────────────────────────

def extract_fields(image_bytes: bytes, category: str) -> Dict[str, Any]:
    """Extract structured fields from a document image.

    For photo categories (vehicle_damage_photo, vehicle_location_photo),
    GPS is extracted from EXIF in Python and merged into the result.

    Args:
        image_bytes: raw image bytes.
        category:    document category string (from VALID_CATEGORIES).

    Returns:
        Dict of extracted fields.  On error returns ``{}``.
    """
    prompt = _PROMPTS.get(category)
    if not prompt:
        logger.warning("No extraction prompt for category '%s'", category)
        return {}

    try:
        img = Image.open(io.BytesIO(image_bytes))
        raw = call_gemini(f"extract_{category}", prompt, img)

        # Parse JSON from response
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            logger.warning("No JSON in extract response for %s: %s", category, raw[:120])
            return {}
        fields: Dict = json.loads(match.group(0))

        # Merge GPS coordinates for photo categories
        if category in ("vehicle_damage_photo", "vehicle_location_photo"):
            lat, lon = _extract_gps_from_exif(image_bytes)
            fields["gps_lat"] = lat
            fields["gps_lon"] = lon

        logger.info("Extracted %d fields for category %s", len(fields), category)
        return fields

    except json.JSONDecodeError as exc:
        logger.error("JSON decode error for %s: %s", category, exc)
        return {}
    except Exception as exc:  # noqa: BLE001
        logger.error("Extraction error for %s: %s", category, exc)
        return {}
