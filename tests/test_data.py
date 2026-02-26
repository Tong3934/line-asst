"""
test_data.py
============
All mock / fixture data used across the test suite.

Covers:
  - Car Damage (CD) policies  — active, expired, inactive, not-found
  - Health (H) policies       — active, expired
  - LINE webhook payloads     — text messages, image messages, postback
  - AI response stubs         — OCR, categorise, extract, damage-analysis
  - Claim folder structures   — status.yaml, extracted_data.json
  - Sample image bytes        — 1×1 pixel JPEG/PNG placeholders
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import date, datetime
from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# 1.  POLICY RECORDS
# ─────────────────────────────────────────────────────────────────────────────

# --- Car Damage (CD) policies ------------------------------------------------

CD_POLICY_ACTIVE_CLASS1: Dict[str, Any] = {
    "policy_number":          "CD-2026-001234",
    "id_card_number":         "3100701443816",
    "title_name":             "นาย",
    "first_name":             "สมชาย ",
    "last_name":              "ใจดี",
    "phone":                  "0812345678",
    "vehicle_plate":          "กก1234",
    "vehicle_brand":          "Toyota",
    "vehicle_model":          "Camry 2.5 HV Premium",
    "vehicle_year":           "2024",
    "vehicle_color":          "White Pearl",
    "coverage_type":          "ชั้น 1",
    "coverage_amount":        1_000_000,
    "deductible":             5_000,
    "insurance_company":      "กรุงเทพประกันภัย",
    "policy_start":           "2026-01-01",
    "policy_end":             "2026-12-31",
    "status":                 "active",
    "policy_document_base64": None,
    # legacy keys used by v1 handlers
    "plate":        "กก1234",
    "car_model":    "Toyota Camry 2.5 HV Premium",
    "car_year":     "2024",
    "insurance_type": "ชั้น 1",
    "cid":          "3100701443816",
}

CD_POLICY_ACTIVE_CLASS2PLUS: Dict[str, Any] = {
    **CD_POLICY_ACTIVE_CLASS1,
    "policy_number":   "CD-2026-002345",
    "id_card_number":  "1234567890123",
    "cid":             "1234567890123",
    "coverage_type":   "ชั้น 2+",
    "insurance_type":  "ชั้น 2+",
    "deductible":      3_000,
    "vehicle_plate":   "ขข5678",
    "plate":           "ขข5678",
    "first_name":      "มานี ",
    "last_name":       "สุขใจ",
}

CD_POLICY_EXPIRED: Dict[str, Any] = {
    **CD_POLICY_ACTIVE_CLASS1,
    "policy_number": "CD-2025-009999",
    "id_card_number": "9999999999999",
    "cid":            "9999999999999",
    "status":         "expired",
    "policy_start":   "2025-01-01",
    "policy_end":     "2025-12-31",
}

CD_POLICY_INACTIVE: Dict[str, Any] = {
    **CD_POLICY_ACTIVE_CLASS1,
    "policy_number": "CD-2026-008888",
    "id_card_number": "8888888888888",
    "cid":            "8888888888888",
    "status":         "inactive",
}

# --- Health (H) policies -----------------------------------------------------

H_POLICY_ACTIVE: Dict[str, Any] = {
    "policy_number":  "H-2026-001001",
    "id_card_number": "3100701443816",
    "title_name":     "นาย",
    "first_name":     "สมชาย ",
    "last_name":      "ใจดี",
    "phone":          "0812345678",
    "plan":           "Gold Health Plus",
    "coverage_ipd":   500_000,
    "coverage_opd":   30_000,
    "room_per_night": 5_000,
    "policy_start":   "2026-01-01",
    "policy_end":     "2026-12-31",
    "status":         "active",
    "cid":            "3100701443816",
}

H_POLICY_EXPIRED: Dict[str, Any] = {
    **H_POLICY_ACTIVE,
    "policy_number": "H-2025-009001",
    "id_card_number": "7777777777777",
    "cid":            "7777777777777",
    "status":         "expired",
    "policy_end":     "2025-12-31",
}

# Convenience map: CID → policy list
POLICY_DB_BY_CID: Dict[str, list] = {
    "3100701443816": [CD_POLICY_ACTIVE_CLASS1, H_POLICY_ACTIVE],
    "1234567890123": [CD_POLICY_ACTIVE_CLASS2PLUS],
    "9999999999999": [CD_POLICY_EXPIRED],
    "8888888888888": [CD_POLICY_INACTIVE],
    "7777777777777": [H_POLICY_EXPIRED],
}

POLICY_DB_BY_PLATE: Dict[str, Dict] = {
    "กก1234": CD_POLICY_ACTIVE_CLASS1,
    "ขข5678": CD_POLICY_ACTIVE_CLASS2PLUS,
}

# ─────────────────────────────────────────────────────────────────────────────
# 2.  CLAIM IDs
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_CLAIM_ID_CD = "CD-20260226-000001"
SAMPLE_CLAIM_ID_H  = "H-20260226-000001"

SEQUENCE_JSON_INITIAL = {"CD": 0, "H": 0}
SEQUENCE_JSON_AFTER_ONE_CD = {"CD": 1, "H": 0}

# ─────────────────────────────────────────────────────────────────────────────
# 3.  LINE USER IDs
# ─────────────────────────────────────────────────────────────────────────────

USER_ID_A = "Uaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
USER_ID_B = "Ubbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

# ─────────────────────────────────────────────────────────────────────────────
# 4.  LINE WEBHOOK PAYLOADS
# ─────────────────────────────────────────────────────────────────────────────

def _text_event(user_id: str, text: str, reply_token: str = "reply_token_001") -> Dict:
    """Build a minimal LINE text-message webhook event body (SDK v3 schema)."""
    return {
        "destination": "U_BOT",
        "events": [
            {
                "replyToken": reply_token,
                "type": "message",
                "mode": "active",
                "timestamp": int(time.time() * 1000),
                "webhookEventId": "01ABCDEFGHIJKLMNOPQRSTUVWX",
                "deliveryContext": {"isRedelivery": False},
                "source": {"type": "user", "userId": user_id},
                "message": {
                    "id": "msg_001",
                    "type": "text",
                    "quoteToken": "q1",
                    "text": text,
                },
            }
        ],
    }


def _image_event(user_id: str, message_id: str = "img_001",
                 reply_token: str = "reply_token_img_001") -> Dict:
    """Build a minimal LINE image-message webhook event body (SDK v3 schema)."""
    return {
        "destination": "U_BOT",
        "events": [
            {
                "replyToken": reply_token,
                "type": "message",
                "mode": "active",
                "timestamp": int(time.time() * 1000),
                "webhookEventId": "01ABCDEFGHIJKLMNOPQRSTUVWX",
                "deliveryContext": {"isRedelivery": False},
                "source": {"type": "user", "userId": user_id},
                "message": {
                    "id": message_id,
                    "type": "image",
                    "quoteToken": "q2",
                    "contentProvider": {"type": "line"},
                },
            }
        ],
    }


# Pre-built webhook bodies used in tests
WEBHOOK_TRIGGER_CD    = _text_event(USER_ID_A, "รถชนครับ")
WEBHOOK_TRIGGER_H     = _text_event(USER_ID_A, "ป่วยต้องนอนโรงพยาบาล")
WEBHOOK_TRIGGER_MAIN  = _text_event(USER_ID_A, "เช็คสิทธิ์เคลมด่วน")
WEBHOOK_AMBIGUOUS     = _text_event(USER_ID_A, "รถชนแล้วต้องไปโรงพยาบาล")
WEBHOOK_CID_TEXT      = _text_event(USER_ID_A, "3100701443816")
WEBHOOK_PLATE_TEXT    = _text_event(USER_ID_A, "กก1234")
WEBHOOK_COUNTERPART_YES   = _text_event(USER_ID_A, "มีคู่กรณี")
WEBHOOK_COUNTERPART_NO    = _text_event(USER_ID_A, "ไม่มีคู่กรณี")
WEBHOOK_SUBMIT        = _text_event(USER_ID_A, "ส่งคำร้อง")
WEBHOOK_CANCEL        = _text_event(USER_ID_A, "ยกเลิก")
WEBHOOK_RESTART       = _text_event(USER_ID_A, "เริ่มใหม่")
WEBHOOK_OWNERSHIP_MINE       = _text_event(USER_ID_A, "ของฉัน (ฝ่ายเรา)")
WEBHOOK_OWNERSHIP_COUNTERPART = _text_event(USER_ID_A, "คู่กรณี (อีกฝ่าย)")
WEBHOOK_IMAGE         = _image_event(USER_ID_A)
WEBHOOK_UNKNOWN_TEXT  = _text_event(USER_ID_A, "hello random text")

# ─────────────────────────────────────────────────────────────────────────────
# 5.  DUMMY IMAGE BYTES  (1×1 JPEG — valid PIL-readable)
# ─────────────────────────────────────────────────────────────────────────────

# Minimal valid 1×1 white JPEG
_MINIMAL_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8U"
    "HRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgN"
    "DRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy"
    "MjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAA"
    "AAAAAAAAAAAAAAAAAP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAA"
    "AAAA/9oADAMBAAIRAxEAPwCwABmX/9k="
)
DUMMY_JPEG_BYTES: bytes = base64.b64decode(_MINIMAL_JPEG_B64)

# Minimal valid 1×1 white PNG
_MINIMAL_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
DUMMY_PNG_BYTES: bytes = base64.b64decode(_MINIMAL_PNG_B64)

# ─────────────────────────────────────────────────────────────────────────────
# 6.  AI RESPONSE STUBS
# ─────────────────────────────────────────────────────────────────────────────

# --- OCR / Identity extraction -----------------------------------------------
OCR_RESPONSE_ID_CARD = {
    "type": "id_card",
    "value": "3100701443816",
}

OCR_RESPONSE_LICENSE_PLATE = {
    "type": "license_plate",
    "value": "กก1234",
}

OCR_RESPONSE_UNKNOWN = {
    "type": "unknown",
    "value": None,
}

# --- Document categorisation -------------------------------------------------
CATEGORISE_DRIVING_LICENSE   = "driving_license"
CATEGORISE_VEHICLE_REG       = "vehicle_registration"
CATEGORISE_CITIZEN_ID        = "citizen_id_card"
CATEGORISE_DAMAGE_PHOTO      = "vehicle_damage_photo"
CATEGORISE_LOCATION_PHOTO    = "vehicle_location_photo"
CATEGORISE_RECEIPT           = "receipt"
CATEGORISE_MED_CERT          = "medical_certificate"
CATEGORISE_ITEMISED_BILL     = "itemised_bill"
CATEGORISE_DISCHARGE         = "discharge_summary"
CATEGORISE_UNKNOWN           = "unknown"

VALID_DOCUMENT_CATEGORIES = [
    CATEGORISE_DRIVING_LICENSE,
    CATEGORISE_VEHICLE_REG,
    CATEGORISE_CITIZEN_ID,
    CATEGORISE_DAMAGE_PHOTO,
    CATEGORISE_LOCATION_PHOTO,
    CATEGORISE_RECEIPT,
    CATEGORISE_MED_CERT,
    CATEGORISE_ITEMISED_BILL,
    CATEGORISE_DISCHARGE,
]

# --- Extracted data stubs ----------------------------------------------------
EXTRACTED_DRIVING_LICENSE = {
    "full_name_th":   "สมชาย ใจดี",
    "full_name_en":   "Somchai Jaidee",
    "license_id":     "12345678",
    "citizen_id":     "3100701443816",
    "date_of_birth":  "1985-03-15",
    "issue_date":     "2022-01-10",
    "expiry_date":    "2027-01-09",
}

EXTRACTED_DRIVING_LICENSE_OTHER_PARTY = {
    "full_name_th":   "พร้อม รักดี",
    "full_name_en":   "Prom Rakdee",
    "license_id":     "87654321",
    "citizen_id":     "1109900112233",
    "date_of_birth":  "1990-07-20",
    "issue_date":     "2021-05-01",
    "expiry_date":    "2026-04-30",
}

EXTRACTED_VEHICLE_REGISTRATION = {
    "plate":          "กก 1234",
    "province":       "กรุงเทพมหานคร",
    "vehicle_type":   "รถยนต์นั่งส่วนบุคคล",
    "brand":          "Toyota",
    "chassis_number": "MR0EX8CD101234567",
    "engine_number":  "2AR1234567",
    "model_year":     "2024",
}

EXTRACTED_DAMAGE_PHOTO = {
    "filename":           "vehicle_damage_photo_1_20260226_120030.jpg",
    "damage_location":    "ประตูซ้ายหน้า",
    "damage_description": "รอยบุบและรอยขูดขีด",
    "severity":           "moderate",
    "gps_lat":            13.7563,
    "gps_lon":            100.5018,
}

EXTRACTED_CITIZEN_ID_CARD = {
    "full_name_th":   "สมชาย ใจดี",
    "full_name_en":   "Somchai Jaidee",
    "citizen_id":     "3100701443816",
    "date_of_birth":  "1985-03-15",
    "issue_date":     "2020-06-01",
    "expiry_date":    "2030-05-31",
}

EXTRACTED_MEDICAL_CERT = {
    "patient_name":  "สมชาย ใจดี",
    "diagnosis":     "ไข้หวัดใหญ่",
    "treatment":     "พักรักษาตัว 3 วัน",
    "doctor_name":   "นพ. สมศักดิ์ รักสุขภาพ",
    "hospital":      "โรงพยาบาลกรุงเทพ",
    "date":          "2026-02-20",
}

EXTRACTED_ITEMISED_BILL = {
    "line_items": [
        {"description": "ค่าห้องพักผู้ป่วยใน", "amount": 2500},
        {"description": "ค่าแพทย์",             "amount": 1000},
        {"description": "ค่ายา",                "amount": 500},
    ],
    "total": 4000,
}

EXTRACTED_RECEIPT = {
    "hospital_name":   "โรงพยาบาลกรุงเทพ",
    "billing_number":  "RC-2026-00123",
    "total_paid":      4000,
    "date":            "2026-02-20",
    "items": [
        {"description": "ค่ารักษาพยาบาลรวม", "amount": 4000}
    ],
}

EXTRACTED_DISCHARGE_SUMMARY = {
    "diagnosis":       "ไข้หวัดใหญ่",
    "treatment":       "ให้ยาต้านไวรัส",
    "admission_date":  "2026-02-18",
    "discharge_date":  "2026-02-20",
}

# --- Damage analysis stubs ---------------------------------------------------
DAMAGE_ANALYSIS_ELIGIBLE = (
    "🟢 **ได้รับสิทธิ์เคลม (แนะนำ)**\n"
    "ประเมินค่าซ่อม: 15,000 บาท\n"
    "โทร 1557\n"
    "*หมายเหตุ: เป็นการประเมินเบื้องต้นโดย AI "
    "โปรดตรวจสอบกับบริษัทประกันอีกครั้ง*"
)

DAMAGE_ANALYSIS_NOT_ELIGIBLE = (
    "🔴 **ไม่สามารถเคลมได้**\n"
    "ประกันชั้น 2+ ต้องมีคู่กรณีเป็นยานพาหนะ\n"
    "โทร 1557\n"
    "*หมายเหตุ: เป็นการประเมินเบื้องต้นโดย AI "
    "โปรดตรวจสอบกับบริษัทประกันอีกครั้ง*"
)

DAMAGE_ANALYSIS_ELIGIBLE_BELOW_EXCESS = (
    "🟡 **ได้รับสิทธิ์เคลม (มีค่าใช้จ่าย)**\n"
    "ค่าซ่อมประเมินต่ำกว่าค่า Excess\n"
    "โทร 1557\n"
    "*หมายเหตุ: เป็นการประเมินเบื้องต้นโดย AI "
    "โปรดตรวจสอบกับบริษัทประกันอีกครั้ง*"
)

# ─────────────────────────────────────────────────────────────────────────────
# 7.  STATUS.YAML CONTENT
# ─────────────────────────────────────────────────────────────────────────────

STATUS_YAML_SUBMITTED = {
    "claim_id":        SAMPLE_CLAIM_ID_CD,
    "claim_type":      "CD",
    "line_user_id":    USER_ID_A,
    "has_counterpart": "มีคู่กรณี",
    "status":          "Submitted",
    "memo":            "",
    "created_at":      "2026-02-26T12:00:00",
    "submitted_at":    "2026-02-26T12:05:30",
    "documents": [
        {"category": "driving_license_customer",    "filename": "driving_license_customer_20260226_120000.jpg",    "useful": None},
        {"category": "driving_license_other_party", "filename": "driving_license_other_party_20260226_120015.jpg", "useful": None},
        {"category": "vehicle_registration",        "filename": "vehicle_registration_20260226_120020.png",        "useful": None},
        {"category": "vehicle_damage_photo",        "filename": "vehicle_damage_photo_1_20260226_120030.jpg",      "useful": None},
    ],
    "metrics": {
        "response_times_ms": [2340, 8120, 15600],
        "total_paid_amount": None,
    },
}

STATUS_YAML_SUBMITTED_HEALTH = {
    "claim_id":        SAMPLE_CLAIM_ID_H,
    "claim_type":      "H",
    "line_user_id":    USER_ID_A,
    "has_counterpart": None,
    "status":          "Submitted",
    "memo":            "",
    "created_at":      "2026-02-26T13:00:00",
    "submitted_at":    "2026-02-26T13:08:00",
    "documents": [
        {"category": "citizen_id_card",     "filename": "citizen_id_card_20260226_130000.jpg",    "useful": None},
        {"category": "medical_certificate", "filename": "medical_certificate_20260226_130100.jpg", "useful": None},
        {"category": "itemised_bill",       "filename": "itemised_bill_20260226_130200.jpg",       "useful": None},
        {"category": "receipt",             "filename": "receipt_20260226_130300.jpg",              "useful": None},
    ],
    "metrics": {
        "response_times_ms": [1200, 9500, 11000, 8750],
        "total_paid_amount": None,
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 8.  EXTRACTED_DATA.JSON CONTENT
# ─────────────────────────────────────────────────────────────────────────────

EXTRACTED_DATA_CD_WITH_COUNTERPART = {
    "driving_license_customer":    EXTRACTED_DRIVING_LICENSE,
    "driving_license_other_party": EXTRACTED_DRIVING_LICENSE_OTHER_PARTY,
    "vehicle_registration":        EXTRACTED_VEHICLE_REGISTRATION,
    "damage_photos": [EXTRACTED_DAMAGE_PHOTO],
    "vehicle_location_photo":      None,
}

EXTRACTED_DATA_CD_NO_COUNTERPART = {
    "driving_license_customer": EXTRACTED_DRIVING_LICENSE,
    "vehicle_registration":     EXTRACTED_VEHICLE_REGISTRATION,
    "damage_photos": [EXTRACTED_DAMAGE_PHOTO],
    "vehicle_location_photo":   None,
}

EXTRACTED_DATA_HEALTH = {
    "citizen_id_card":     EXTRACTED_CITIZEN_ID_CARD,
    "medical_certificate": EXTRACTED_MEDICAL_CERT,
    "itemised_bill":       EXTRACTED_ITEMISED_BILL,
    "discharge_summary":   None,
    "medical_receipts": [EXTRACTED_RECEIPT],
}

# ─────────────────────────────────────────────────────────────────────────────
# 9.  KEYWORD SETS
# ─────────────────────────────────────────────────────────────────────────────

CD_KEYWORDS = ["รถ", "ชน", "เฉี่ยว", "ขโมย", "หาย", "car", "vehicle", "accident", "damage", "crash"]
H_KEYWORDS  = ["เจ็บ", "ป่วย", "ผ่าตัด", "โรงพยาบาล", "health", "sick", "hospital", "medical", "surgery"]

CANCEL_KEYWORDS = ["ยกเลิก", "cancel", "เริ่มใหม่", "restart"]

# ─────────────────────────────────────────────────────────────────────────────
# 10. REQUIRED DOCS per claim type / sub-type
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_DOCS_CD_WITH_COUNTERPART = [
    "driving_license_customer",
    "driving_license_other_party",
    "vehicle_registration",
    "vehicle_damage_photo",
]

REQUIRED_DOCS_CD_NO_COUNTERPART = [
    "driving_license_customer",
    "vehicle_registration",
    "vehicle_damage_photo",
]

REQUIRED_DOCS_HEALTH = [
    "citizen_id_card",
    "medical_certificate",
    "itemised_bill",
    "receipt",
]

OPTIONAL_DOCS_CD     = ["vehicle_location_photo"]
OPTIONAL_DOCS_HEALTH = ["discharge_summary"]

# ─────────────────────────────────────────────────────────────────────────────
# 11. CLAIM STATUS LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

VALID_STATUS_TRANSITIONS: Dict[str, list] = {
    "Submitted":    ["Under Review"],
    "Under Review": ["Pending", "Approved", "Rejected"],
    "Pending":      ["Under Review", "Rejected"],
    "Approved":     ["Paid"],
    "Rejected":     [],
    "Paid":         [],
}

# ─────────────────────────────────────────────────────────────────────────────
# 12. WEBHOOK SIGNATURE HELPER
# ─────────────────────────────────────────────────────────────────────────────

MOCK_CHANNEL_SECRET = "test_channel_secret_1234567890ab"
MOCK_CHANNEL_ACCESS_TOKEN = "test_access_token_xyz"


def make_line_signature(body: bytes, channel_secret: str = MOCK_CHANNEL_SECRET) -> str:
    """Compute the correct X-Line-Signature for a webhook body."""
    mac = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    )
    return base64.b64encode(mac.digest()).decode("utf-8")


def make_webhook_body(payload: Dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# 13. BUDDHIST ERA DATE CONVERSION TEST CASES
# ─────────────────────────────────────────────────────────────────────────────

# (buddhist_era_str, expected_gregorian_str)
BUDDHIST_ERA_CONVERSION_CASES = [
    ("2567",     "2024"),
    ("2568",     "2025"),
    ("2565-06-01", "2022-06-01"),
    ("2570-12-31", "2027-12-31"),
]

# ─────────────────────────────────────────────────────────────────────────────
# 14. CLAIM ID FORMAT
# ─────────────────────────────────────────────────────────────────────────────

VALID_CLAIM_ID_CASES = [
    "CD-20260226-000001",
    "CD-20260226-000042",
    "H-20260226-000001",
    "H-20260226-999999",
]

INVALID_CLAIM_ID_CASES = [
    "XX-20260226-000001",  # bad prefix
    "CD-2026226-000001",   # date wrong length
    "CD-20260226-00001",   # seq too short
    "CD20260226000001",    # missing dashes
]
