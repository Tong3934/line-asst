"""
constants.py — Application-wide constants.

12-Factor III: All tunable values can be overridden via environment variables.
Never hard-code credentials here — use .env / Kubernetes Secrets.
"""

import os

# ── AI Model ──────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

# ── Gemini Token Pricing (USD per 1 000 tokens) ───────────────────────────────
# Update when Google changes GA pricing.  Override via env in production.
PRICE_INPUT_PER_1K: float  = float(os.getenv("GEMINI_PRICE_INPUT",  "0.00035"))
PRICE_OUTPUT_PER_1K: float = float(os.getenv("GEMINI_PRICE_OUTPUT", "0.00105"))

# ── Storage ───────────────────────────────────────────────────────────────────
DATA_DIR: str = os.getenv("DATA_DIR", "/data")

# ── LINE API Hosts (overridable for mock-chat testing) ────────────────────────
LINE_API_HOST: str      = os.getenv("LINE_API_HOST",      "https://api.line.me")
LINE_DATA_API_HOST: str = os.getenv("LINE_DATA_API_HOST", "https://api-data.line.me")

# ── Valid document categories (exact strings returned / expected by AI) ───────
VALID_CATEGORIES: frozenset = frozenset({
    "driving_license",
    "vehicle_registration",
    "citizen_id_card",
    "receipt",
    "medical_certificate",
    "itemised_bill",
    "discharge_summary",
    "vehicle_damage_photo",
    "vehicle_location_photo",
})

# ── Required documents per claim type / sub-type ─────────────────────────────
REQUIRED_DOCS: dict = {
    "CD": {
        "มีคู่กรณี": [
            "driving_license_customer",
            "driving_license_other_party",
            "vehicle_registration",
            "vehicle_damage_photo",
        ],
        "ไม่มีคู่กรณี": [
            "driving_license_customer",
            "vehicle_registration",
            "vehicle_damage_photo",
        ],
    },
    "H": {
        None: [
            "citizen_id_card",
            "medical_certificate",
            "itemised_bill",
            "receipt",
        ],
    },
}

# Optional docs (accepted but not blocking submission)
OPTIONAL_DOCS: dict = {
    "CD": ["vehicle_location_photo"],
    "H":  ["discharge_summary"],
}

# ── Claim Status Lifecycle ────────────────────────────────────────────────────
# Maps current status → list of allowed next statuses (Reviewer dashboard)
VALID_TRANSITIONS: dict = {
    "Submitted":    ["Under Review"],
    "Under Review": ["Pending", "Approved", "Rejected"],
    "Pending":      ["Under Review", "Rejected"],
    "Approved":     ["Paid"],
}

ALL_STATUSES: tuple = (
    "Submitted", "Under Review", "Pending", "Approved", "Rejected", "Paid"
)

# ── Conversation Cancel Keywords ─────────────────────────────────────────────
CANCEL_KEYWORDS: frozenset = frozenset({
    "ยกเลิก", "cancel", "เริ่มใหม่", "restart",
})

# ── Claim-Type Detection Keywords ─────────────────────────────────────────────
CD_KEYWORDS: frozenset = frozenset({
    "รถ", "ชน", "เฉี่ยว", "ขโมย", "หาย",
    "car", "vehicle", "accident", "damage", "crash",
})
H_KEYWORDS: frozenset = frozenset({
    "เจ็บ", "ป่วย", "ผ่าตัด", "โรงพยาบาล",
    "health", "sick", "hospital", "medical", "surgery",
})

# ── Trigger keyword for the full claim flow ───────────────────────────────────
TRIGGER_KEYWORDS: frozenset = frozenset({
    "เช็คสิทธิ์เคลมด่วน", "เช็คสิทธิ์", "เคลม",
    "claim", "insurance",
})

# ── Log settings ──────────────────────────────────────────────────────────────
LOG_MAX_BYTES: int   = 10 * 1024 * 1024  # 10 MB per rotating log file
LOG_BACKUP_COUNT: int = 7                 # 7 rotated files → ~70 MB max
LOG_MAX_MEMORY: int  = 2_000             # max entries kept in memory for Admin dashboard
TOKEN_RECORD_MAX: int = 10_000           # max per-month token records kept

# ── Application version ───────────────────────────────────────────────────────
APP_VERSION: str = "2.0.0"
