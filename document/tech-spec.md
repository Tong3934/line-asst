# Technical Specification — LINE Insurance Claim Bot
## เช็คสิทธิ์ & เคลมประกันด่วน — v2.0

**Spec Version:** 2.1  
**BRD Reference:** [business-requirement.md](business-requirement.md) v2.0  
**User Journey Reference:** [user-journey.md](user-journey.md) v2.0  
**Last Updated:** February 26, 2026  
**Authors:** Technical Development Team

---

## ⚠️ Implementation Status Overview

This document reflects the **actual current state** of the codebase as of February 26, 2026.

| Area | Status | Notes |
|---|---|---|
| Core bot (v1.0 flow) | ✅ Live | Active in `main.py`; v1.0 state names, CD-only, damage-analysis flow |
| New AI package (`ai/`) | ✅ Built | `ocr`, `categorise`, `extract`, `analyse_damage` — all implemented |
| New Storage package (`storage/`) | ✅ Built | `claim_store`, `document_store`, `sequence` — all implemented |
| New Handlers (`handlers/`) | ✅ Built | `trigger`, `identity`, `documents`, `submit` — all implemented |
| Web Dashboards (`dashboards/`) | ✅ Built | `reviewer.html`, `manager.html`, `admin.html` — all implemented |
| Tests | ✅ 338 passing | 10 test files; `pytest tests/ -v` |
| **Wire v2.0 packages into `main.py`** | ❌ Gap | `main.py` still runs v1.0 monolithic logic; new packages not yet imported |
| Health (H) claim type | ❌ Not yet | v2.0 handler package supports it; `main.py` does not route to it |
| `mock_chat.py` | ❌ Missing | Referenced in `docker-compose.yml`; `--profile dev` will crash |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure (Current)](#3-repository-structure-current)
4. [Environment Variables](#4-environment-variables)
5. [Data Models](#5-data-models)
6. [Conversation State Machine](#6-conversation-state-machine)
7. [LINE Bot — Message Handlers](#7-line-bot--message-handlers)
8. [AI Integration (Google Gemini)](#8-ai-integration-google-gemini)
9. [Storage Layer](#9-storage-layer)
10. [Claim ID Sequence Generator](#10-claim-id-sequence-generator)
11. [Web Dashboards](#11-web-dashboards)
12. [FastAPI Endpoints (Full)](#12-fastapi-endpoints-full)
13. [LINE Flex Message Components](#13-line-flex-message-components)
14. [Docker & Deployment](#14-docker--deployment)
15. [Non-Functional Requirements](#15-non-functional-requirements)
16. [Remaining Migration Steps](#16-remaining-migration-steps)
17. [Open Questions](#17-open-questions)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LINE Platform                            │
│  Customer LINE App ──► LINE Messaging API ──► POST /webhook     │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Docker Compose Host                             │
│                                                                 │
│  ┌──────────────────────┐   ┌─────────────┐  ┌──────────────┐  │
│  │   line-bot :8000     │   │  ngrok      │  │  mock-chat   │  │
│  │   FastAPI            │◄──│  :4040      │  │  :8001       │  │
│  │   (bot + dashboards) │   │  (webhook)  │  │  (dev only)  │  │
│  └──────────┬───────────┘   └─────────────┘  └──────────────┘  │
│             │                                                   │
│  ┌──────────▼────────────────────────────────────────────────┐  │
│  │   /data  Docker Volume (persistent storage)               │  │
│  │   /data/claims/                                           │  │
│  │   /data/sequence.json                                     │  │
│  │   /data/logs/                                             │  │
│  │   /data/token_records/                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│  External Services                                              │
│  • Google Gemini AI   (models/gemini-2.5-flash)                 │
│  • LINE Data API      (api-data.line.me)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Role → URL Routing

| Role | URL | Notes |
|---|---|---|
| Customer | LINE App only | No browser URL |
| Reviewer | `GET /reviewer` | Claims review dashboard |
| Manager | `GET /manager` | Analytics dashboard |
| Admin | `GET /admin` | Logs + AI token usage |
| LINE Platform | `POST /webhook` or `POST /callback` | Webhook events (both paths handled) |
| Health probe | `GET /health` | LINE + Gemini config status |

---

## 2. Technology Stack

| Layer | Technology | Status |
|---|---|---|
| Language | Python 3.11 | Existing |
| Web framework | FastAPI | Existing |
| ASGI server | Uvicorn | Existing |
| LINE Bot SDK | `line-bot-sdk` v3 | Existing |
| AI | Google Gemini `models/gemini-2.5-flash` | Existing |
| Image processing | Pillow | Existing |
| HTTP client | httpx | Existing |
| Config | python-dotenv | Existing |
| YAML read/write | `pyyaml` | ✅ Present in `requirements.txt` |
| Web dashboard HTML | Jinja2 templates | ✅ Present in `requirements.txt` |
| Async file I/O | `aiofiles` | ✅ Present in `requirements.txt` |
| Containerisation | Docker + Docker Compose | Existing |
| Tunnelling (dev) | ngrok via `pyngrok` | ✅ Present in `requirements.txt` |
| Test framework | pytest + pytest-asyncio | See `requirements_test.txt` |

---

## 3. Repository Structure (Current)

```
line-asst/
├── main.py                  # FastAPI app — bot handlers + dashboard endpoints (359 lines)
├── config.py                # NEW — env vars, LINE config, Gemini model init
├── session_manager.py       # NEW — user_sessions dict + get/set/reset/process_search_result
├── claim_engine.py          # NEW — extract_info_from_image, analyze_damage, start_claim_analysis
├── flex_messages.py         # All LINE Flex Message / QuickReply builders
├── constants.py             # Shared constants: model, pricing, DATA_DIR, keywords, categories
├── mock_data.py             # Policy lookup (mock DB — ~1.5 MB)
├── ngrok.py                 # Dev-only pyngrok tunnel launcher
│
├── handlers/                # v2.0 conversation handlers (BUILT, not yet wired into main.py)
│   ├── __init__.py
│   ├── trigger.py           # Claim type detection, session init, Claim ID
│   ├── identity.py          # Policy verification (text + OCR path)
│   ├── documents.py         # Upload loop, categorise, extract, ownership ✅ IMPLEMENTED
│   └── submit.py            # Completeness check + submission ✅ IMPLEMENTED
│
├── ai/                      # All AI operations isolated here
│   ├── __init__.py          # Shared Gemini client + _call_gemini wrapper + token tracking
│   ├── categorise.py        # categorise_document(image_bytes) → str
│   ├── extract.py           # extract_fields(image_bytes, category) → Dict
│   ├── analyse_damage.py    # analyse_damage(...) → str
│   └── ocr.py               # extract_id_from_image(image_bytes) → Dict
│
├── storage/                 # All file I/O isolated here
│   ├── __init__.py
│   ├── claim_store.py       # Read/write status.yaml, extracted_data.json
│   ├── document_store.py    # Save/read document image files
│   └── sequence.py          # Claim ID counter (sequence.json)
│
├── dashboards/              # Web dashboard HTML templates ✅ ALL BUILT
│   ├── reviewer.html
│   ├── manager.html
│   └── admin.html
│
├── tests/                   # Test suite — 338 tests passing
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures (app_client, mocks)
│   ├── test_data.py         # Fixture data & canned responses
│   ├── test_api_endpoints.py
│   ├── test_business_logic.py
│   ├── test_claim_engine.py
│   ├── test_conversation_flows.py
│   ├── test_flex_messages.py
│   ├── test_session_manager.py
│   └── test_webhook_security.py
│
├── conftest.py              # Root-level conftest (project-wide fixtures)
├── pytest.ini               # Test config: markers, asyncio_mode=auto, timeout=30
├── requirements.txt         # Runtime dependencies
├── requirements_test.txt    # Test-only dependencies
├── dockerfile
├── docker-compose.yml       # Has claim-data volume; mock-chat profile
├── entrypoint.sh            # git-pull + data dir init + sequence.json seed
├── nginx.conf               # Inactive (reverse proxy config, not in compose)
├── .env.example
├── .gitignore
│
├── SYSTEM_SPEC.md           # Concise system spec (for team onboarding)
│
└── document/
    ├── tech-spec.md         # This file
    ├── business-requirement.md
    ├── user-journey.md
    └── document-verify.md
```

> ⚠️ **MISSING:** `mock_chat.py` — `docker-compose.yml` runs `python mock_chat.py` for the `mock-chat` service. `docker compose --profile dev up` will crash until this file is created.

---

## 4. Environment Variables

All variables loaded from `.env` via `python-dotenv` in `config.py`. The app raises `ValueError` on startup if required variables are missing.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | — | LINE Messaging API access token |
| `LINE_CHANNEL_SECRET` | ✅ | — | LINE webhook signature secret |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `NGROK_AUTHTOKEN` | ✅ (Docker) | — | ngrok tunnel auth token |
| `PORT` | ❌ | `8000` | Uvicorn listen port |
| `DATA_DIR` | ❌ | `/data` | Root path for the persistent volume |
| `GEMINI_MODEL` | ❌ | `models/gemini-2.5-flash` | Override Gemini model name |
| `GEMINI_PRICE_INPUT` | ❌ | `0.00035` | USD per 1K input tokens |
| `GEMINI_PRICE_OUTPUT` | ❌ | `0.00105` | USD per 1K output tokens |
| `LINE_API_HOST` | ❌ | `https://api.line.me` | Override for mock testing |
| `LINE_DATA_API_HOST` | ❌ | `https://api-data.line.me` | Override for mock testing |
| `BOT_URL` | ❌ | `http://localhost:8000` | Used by `mock_chat.py` to reach the bot |
| `REPO_URL` | ❌ | — | Git repo URL (auto-pull via `entrypoint.sh`) |
| `BRANCH` | ❌ | — | Git branch for auto-pull |

---

## 5. Data Models

### 5.1 Session (`user_sessions` dict — in-memory)

Managed by `session_manager.py`. `user_sessions` is a module-level dict imported by `main.py`.

```python
# v1.0 active states (current main.py flow)
user_sessions: Dict[str, Dict] = {
    "<line_user_id>": {
        "state":           str,          # See §6 for all valid states
        "policy_info":     Dict,         # Full policy record from mock_data
        "has_counterpart": str | None,   # "มีคู่กรณี" | "ไม่มีคู่กรณี"
        "search_results":  List[Dict],   # Populated in vehicle-selection state
        "temp_image_bytes": bytes,       # Damage image bytes (v1.0 flow)
        "additional_info": str | None,   # Free-text incident description

        # v2.0 fields (used by handlers/ package when wired in)
        "claim_id":        str,          # e.g. "CD-20260226-000001"
        "claim_type":      str,          # "CD" | "H"
        "uploaded_docs":   Dict[str, str],  # {doc_category: filename}
        "awaiting_ownership_for": Dict | str | None,  # pending DL assignment
    }
}
```

**State is the single source of truth** for routing every incoming message or image.

---

### 5.2 Policy Record

Two flavours — Car Damage and Health. Both stored as Python dicts (PoC: from `mock_data.py`).

**Car Damage Policy:**

```python
{
    "policy_number":          str,   # "CD-2026-001234"
    "id_card_number":         str,   # 13-digit string
    "title_name":             str,
    "first_name":             str,   # may have trailing space — use .strip()
    "last_name":              str,
    "phone":                  str,
    "plate":                  str,   # "กก 1234" (used in mock_data)
    "car_model":              str,   # used in claim_engine prompts
    "car_year":               str,
    "vehicle_brand":          str,
    "vehicle_model":          str,
    "vehicle_year":           str,
    "vehicle_color":          str,
    "coverage_type":          str,   # "ชั้น 1" | "ชั้น 2+" | "ชั้น 2" | "ชั้น 3+" | "ชั้น 3"
    "coverage_amount":        int,   # THB
    "deductible":             int,   # THB
    "insurance_company":      str,
    "policy_start":           str,   # "YYYY-MM-DD"
    "policy_end":             str,   # "YYYY-MM-DD"
    "status":                 str,   # "active" | "expired" | "inactive"
    "policy_document_base64": str | None,  # Base64 PDF for damage analysis
}
```

**Health Policy:**

```python
{
    "policy_number":   str,
    "id_card_number":  str,
    "title_name":      str,
    "first_name":      str,
    "last_name":       str,
    "phone":           str,
    "plan":            str,   # "Gold Health Plus" etc.
    "coverage_ipd":    int,   # THB
    "coverage_opd":    int,   # THB
    "room_per_night":  int,   # THB
    "policy_start":    str,   # "YYYY-MM-DD"
    "policy_end":      str,   # "YYYY-MM-DD"
    "status":          str,
}
```

---

### 5.3 Per-Claim Folder Layout (`/data/claims/{CLAIM_ID}/`)

```
CD-20260226-000001/
  status.yaml             ← claim metadata (see §5.4)
  extracted_data.json     ← all AI field extractions (see §5.5)
  summary.md              ← AI-generated claim summary (generated on submit)
  documents/
    driving_license_customer_20260226_120000.jpg
    driving_license_other_party_20260226_120015.jpg
    vehicle_registration_20260226_120020.png
    vehicle_damage_photo_1_20260226_120030.jpg
    vehicle_location_photo_20260226_120045.jpg
```

---

### 5.4 `status.yaml` Schema

```yaml
claim_id: "CD-20260226-000001"
claim_type: "CD"                      # "CD" | "H"
line_user_id: "U..."
has_counterpart: "มีคู่กรณี"          # CD only; null for H
status: "Submitted"                   # See lifecycle §5.7
memo: ""
created_at: "2026-02-26T12:00:00"
submitted_at: "2026-02-26T12:05:30"
documents:
  - category: "driving_license_customer"
    filename: "driving_license_customer_20260226_120000.jpg"
    useful: null                      # null | true | false (set by Reviewer)
  - category: "vehicle_damage_photo_1"
    filename: "vehicle_damage_photo_1_20260226_120030.jpg"
    useful: null
metrics:
  response_times_ms: [2340, 8120, 15600]
  total_paid_amount: null             # Set when status → Paid
```

---

### 5.5 `extracted_data.json` Schema

Only keys relevant to the claim type are populated. Fields not read by AI are stored as `null`.  
All dates stored as `YYYY-MM-DD` (Gregorian; convert from Buddhist Era where needed — see §8.4).

**Car Damage:**

```json
{
  "driving_license_customer": {
    "full_name_th": "สมชาย ใจดี",
    "full_name_en": "Somchai Jaidee",
    "license_id": "12345678",
    "citizen_id": "3100701443816",
    "date_of_birth": "1985-03-15",
    "issue_date": "2022-01-10",
    "expiry_date": "2027-01-09"
  },
  "driving_license_other_party": {},
  "vehicle_registration": {
    "plate": "กก 1234",
    "province": "กรุงเทพมหานคร",
    "vehicle_type": "รถยนต์นั่งส่วนบุคคล",
    "brand": "Toyota",
    "chassis_number": "MR0EX8CD101234567",
    "engine_number": "2AR1234567",
    "model_year": "2024"
  },
  "vehicle_damage_photo_1": {
    "filename": "vehicle_damage_photo_1_20260226_120030.jpg",
    "damage_location": "ประตูซ้ายหน้า",
    "damage_description": "รอยบุบและรอยขูดขีด",
    "severity": "moderate",
    "gps_lat": 13.7563,
    "gps_lon": 100.5018
  },
  "vehicle_location_photo": {
    "filename": "vehicle_location_photo_20260226_120045.jpg",
    "location_description": "ถนนพระราม 9",
    "road_conditions": "แห้ง",
    "weather_conditions": "แดด",
    "gps_lat": null,
    "gps_lon": null
  }
}
```

**Health:**

```json
{
  "citizen_id_card": {
    "full_name_th": "...", "full_name_en": "...",
    "citizen_id": "...", "date_of_birth": "...",
    "issue_date": "...", "expiry_date": "..."
  },
  "medical_certificate": {
    "patient_name": "...", "diagnosis": "...",
    "treatment": "...", "doctor_name": "...",
    "hospital": "...", "date": "..."
  },
  "itemised_bill": {
    "line_items": [{"description": "...", "amount": 1500}],
    "total": 4500
  },
  "discharge_summary": {
    "diagnosis": "...", "treatment": "...",
    "admission_date": "...", "discharge_date": "..."
  },
  "receipt_1": {
    "filename": "receipt_1_20260226_130000.jpg",
    "hospital_name": "...", "billing_number": "...",
    "total_paid": 4500, "date": "...",
    "items": [{"description": "...", "amount": 4500}]
  }
}
```

---

### 5.6 `sequence.json` (Claim ID Counters)

```json
{
  "CD": 12,
  "H": 3
}
```

- Incremented atomically at claim creation.
- Stored at `{DATA_DIR}/sequence.json`.
- Seeded by `entrypoint.sh` on first run.
- Format: `{type}-{YYYYMMDD}-{counter:06d}` → `CD-20260226-000013`

---

### 5.7 Claim Status Lifecycle

```
Submitted → Under Review → Pending → Approved → Paid
                         ↘
                          Rejected
```

Valid transitions enforced in the Reviewer dashboard and in `constants.py`:

| From | Allowed next values |
|---|---|
| Submitted | Under Review |
| Under Review | Pending, Approved, Rejected |
| Pending | Under Review, Rejected |
| Approved | Paid |

---

## 6. Conversation State Machine

### 6.1 Active v1.0 States (current `main.py`)

These are the state names that `main.py` currently uses. The v1.0 flow handles Car Damage (CD) with eligibility analysis only.

| State | Meaning | Handler |
|---|---|---|
| `idle` / `None` | No active session | Falls to welcome + QuickReply |
| `waiting_for_info` | Asking CID / plate / name / image | `handle_text_message`, `handle_image_message` |
| `waiting_for_vehicle_selection` | Multiple policies found | `handle_text_message` |
| `waiting_for_counterpart` | CD: asking มีคู่กรณี / ไม่มีคู่กรณี | `handle_text_message` |
| `waiting_for_image` | Damage photo expected | `handle_image_message` |
| `waiting_for_additional_info` | Free-text incident description | `handle_text_message` |
| `completed` | Analysis done | `handle_text_message` |
| `waiting_for_claim_documents` | Document upload phase (basic, no categorisation) | `handle_image_message` |

### 6.2 v2.0 Target States (defined in `handlers/` package)

These states are implemented in the `handlers/` package but **not yet wired into `main.py`**:

`idle` → `detecting_claim_type` → `verifying_policy` → `waiting_for_vehicle_selection` → `waiting_for_counterpart` → `uploading_documents` → `awaiting_ownership` → `ready_to_submit` → `submitted`

> ⚠️ **Critical for the next developer:** The v1.0 state names and the v2.0 state names are **different**. When wiring v2.0 into `main.py`, the entire state machine must be rewritten using the v2.0 names. Do NOT mix them.

### 6.3 Full v2.0 State Diagram (Target)

```
              ┌─────────────────────────────────────────────────────────────────┐
              │  Cancel keywords ("ยกเลิก","cancel","เริ่มใหม่") from any state │
              ▼                                                                  │
          [idle]                                                                 │
              │ CD/H keyword or "เช็คสิทธิ์เคลมด่วน" detected                  │
              ▼                                                                  │
      [detecting_claim_type]                                                     │
              │ CD or H confirmed                                                │
              ▼                                                                  │
      [verifying_policy]  ◄── retry if not found / expired                      │
              │ Policy found                                                     │
     ┌────────┴────────┐                                                         │
     │ CD              │ H                                                       │
     ▼                 └──────────────────────────┐                             │
[waiting_for_counterpart]                         │                             │
     │ Answered                                   │                             │
     ▼                                            ▼                             │
[uploading_documents] ◄────────────── [uploading_documents]                    │
     │  Driving license (CD with-counterpart)                                   │
     ▼                                                                          │
[awaiting_ownership]                                                             │
     │ Ownership confirmed                                                       │
     ▼                                                                          │
[uploading_documents]  ◄── loop until all required docs received                │
     │ All docs complete                                                         │
     ▼                                                                          │
[ready_to_submit]                                                               │
     │ Customer taps Submit                                                      │
     ▼                                                                          │
 [submitted] ─────────────────────────────────────────────────────────────────┘
```

### 6.4 Required Documents Per Claim Type

| Claim Type | Sub-type | Required storage keys |
|---|---|---|
| CD | มีคู่กรณี | `driving_license_customer`, `driving_license_other_party`, `vehicle_registration`, `vehicle_damage_photo` (≥1) |
| CD | ไม่มีคู่กรณี | `driving_license_customer`, `vehicle_registration`, `vehicle_damage_photo` (≥1) |
| H | — | `citizen_id_card`, `medical_certificate`, `itemised_bill`, `receipt` (≥1) |

Optional (accepted but not blocking submission):

| Claim Type | Optional keys |
|---|---|
| CD | `vehicle_location_photo` |
| H | `discharge_summary` |

Defined in `constants.py` as `REQUIRED_DOCS` and `OPTIONAL_DOCS`.

---

## 7. LINE Bot — Message Handlers

### 7.1 Module Architecture

`main.py` delegates to three focused modules:

| Module | Responsibility |
|---|---|
| `config.py` | Load env vars; create LINE `Configuration`, `WebhookHandler`, Gemini model |
| `session_manager.py` | `user_sessions` dict; `get_session`, `set_state`, `reset_session`, `process_search_result` |
| `claim_engine.py` | `extract_info_from_image_with_gemini`, `analyze_damage_with_gemini`, `start_claim_analysis`, `extract_phone_from_response` |

### 7.2 Text Message Handler (`handle_text_message`) — v1.0 Active Flow

Evaluation order (first match wins):

```
1. text == "เช็คสิทธิ์เคลมด่วน"              → state = "waiting_for_info"; send request_info_flex
2. state == "waiting_for_info"              → regex-based CID/phone/plate/name search
3. state == "waiting_for_vehicle_selection" → "เลือกรถ:{plate}" → process_search_result
4. state == "waiting_for_counterpart"       → record has_counterpart; state = "waiting_for_image"
5. state == "waiting_for_additional_info"   → pass additional_info to start_claim_analysis
6. state == "completed" + text == "ส่งเคลม" → state = "waiting_for_claim_documents"
7. state == "completed" + text == "จบการสนทนา" → reset session
8. state == "waiting_for_claim_documents" + text == "เสร็จสิ้น" → reset session; thank user
9. fallback (idle/None/completed)          → welcome + QuickReply "เช็คสิทธิ์เคลมด่วน"
```

**Policy lookup in `waiting_for_info`:**
- `^\d{13}$` → `search_policies_by_cid`
- `^\d{9,10}$` → `search_policies_by_phone`
- Plate text → `search_policies_by_plate`
- Else → `search_policies_by_name`

### 7.3 Image Message Handler (`handle_image_message`) — v1.0 Active Flow

```
Download image: GET https://api-data.line.me/v2/bot/message/{id}/content

state == "waiting_for_info":
  → extract_info_from_image_with_gemini (OCR)
  → search by id_card CID or license_plate
  → process_search_result(..., use_push=True)

state == "waiting_for_image":
  → store image_bytes in session["temp_image_bytes"]
  → state = "waiting_for_additional_info"
  → show additional_info_prompt_flex

state == "waiting_for_claim_documents":
  → acknowledge receipt; remind user to type "เสร็จสิ้น"

else:
  → "กรุณาทำตามขั้นตอนก่อน" message
```

> ⚠️ **v2.0 gap:** The `handlers/documents.py` pipeline (categorise → extract → ownership QuickReply → checklist) is implemented and tested but `handle_image_message` in `main.py` does not yet call it.

### 7.4 process_search_result (in `session_manager.py`)

Handles all three policy-count outcomes:

| Outcome | State | Bot action |
|---|---|---|
| 0 policies | unchanged | Error message |
| >1 policies | `waiting_for_vehicle_selection` | `create_vehicle_selection_flex` carousel |
| 1 policy | `waiting_for_counterpart` | `create_policy_info_flex` + counterpart QuickReply |

---

## 8. AI Integration (Google Gemini)

All Gemini calls in the `ai/` package share a wrapper (`_call_gemini` in `ai/__init__.py`) that:
- Records token usage → `/data/token_records/YYYY-MM.jsonl`
- Catches `429 Resource Exhausted` → returns user-friendly retry message
- Deletes any uploaded Gemini files in a `finally` block

### 8.1 `ai.ocr.extract_id_from_image(image_bytes) → Dict`

Formerly `extract_info_from_image_with_gemini` in `main.py`/`claim_engine.py`.

- Returns `{"type": "id_card"|"license_plate"|"unknown", "value": str|None}`

> Note: `claim_engine.py` still contains its own `extract_info_from_image_with_gemini` for the v1.0 flow. When `main.py` is updated to use v2.0 packages, `claim_engine.py` OCR will be replaced by `ai.ocr`.

---

### 8.2 `ai.categorise.categorise_document(image_bytes) → str`

Single Gemini vision call.

Valid return values (exact strings; defined in `constants.VALID_CATEGORIES`):

```
driving_license          vehicle_registration     citizen_id_card
receipt                  medical_certificate      itemised_bill
discharge_summary        vehicle_damage_photo     vehicle_location_photo
unknown
```

If response is not in the above set → treat as `"unknown"`.

---

### 8.3 `ai.extract.extract_fields(image_bytes, category) → Dict`

Different prompt per category. All prompts enforce:

1. **Buddhist Era conversion (BR-02):** "Convert all dates from Buddhist Era to Gregorian by subtracting 543. Return all dates as YYYY-MM-DD."
2. **Null for unreadable fields (FR-04.3):** "If a field cannot be read clearly, return null. Never guess."
3. **GPS extraction:** For `vehicle_damage_photo` and `vehicle_location_photo`, extract GPS decimal degrees from EXIF via Pillow before calling Gemini. Do not ask Gemini to read EXIF.
4. **JSON only:** "Return only valid JSON. No markdown, no prose."

Returns a dict matching the schema in §5.5. On error returns `{}`.

---

### 8.4 `ai.analyse_damage.analyse_damage(...)` → str

In `claim_engine.py` as `analyze_damage_with_gemini` (for v1.0 flow). Also available in `ai/analyse_damage.py` (for v2.0 package).

- Requires `policy_info["policy_document_base64"]` — returns error message if missing.
- Uploads PDF via `genai.upload_file` inside `try/finally` that always deletes.
- System prompt injects `has_counterpart` and `additional_info`.
- Response includes eligibility verdict + 3-step action plan.

Eligibility logic embedded in prompt:

| Insurance Class | ไม่มีคู่กรณี | มีคู่กรณี |
|:---:|:---:|:---:|
| ชั้น 1 | ✅ | ✅ |
| ชั้น 2+ / ชั้น 2 | ❌ | ✅ |
| ชั้น 3+ / ชั้น 3 | ❌ | ✅ |

---

### 8.5 Gemini File Upload Pattern

```python
uploaded = None
tmp = None
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as f:
        f.write(pdf_bytes); tmp = f.name
    uploaded = genai.upload_file(tmp, mime_type="application/pdf")
    time.sleep(2)
    response = gemini_model.generate_content([prompt, damage_img, uploaded])
    return response.text
finally:
    if uploaded:
        try: genai.delete_file(uploaded.name)
        except: pass
    if tmp and os.path.exists(tmp):
        os.unlink(tmp)
```

---

### 8.6 Token Record Format

Append one JSON line per call to `/data/token_records/YYYY-MM.jsonl`:

```json
{"ts":"2026-02-26T12:05:30","operation":"categorise_document","model":"gemini-2.5-flash","input_tokens":512,"output_tokens":32,"total_tokens":544,"cost_usd":0.0012}
```

Pricing constants in `constants.py`:

```python
PRICE_INPUT_PER_1K:  float = float(os.getenv("GEMINI_PRICE_INPUT",  "0.00035"))
PRICE_OUTPUT_PER_1K: float = float(os.getenv("GEMINI_PRICE_OUTPUT", "0.00105"))
```

---

## 9. Storage Layer

All file I/O is isolated in `storage/`. No code outside this package reads or writes files directly.

### 9.1 `storage.claim_store` — Public API

```python
def create_claim(claim_id, claim_type, line_user_id, has_counterpart) -> None:
    """Create folder, empty extracted_data.json, initial status.yaml."""

def get_claim_status(claim_id) -> Dict:
    """Read and return status.yaml as dict."""

def update_claim_status(claim_id, status, memo=None, paid_amount=None, submitted_at=None) -> None:
    """Update status (and optionally memo/paid_amount/submitted_at) in status.yaml."""

def mark_document_useful(claim_id, filename, useful: bool) -> None:
    """Set useful flag on one document in status.yaml."""

def add_document_to_claim(claim_id, category, filename) -> None:
    """Append a document entry (with useful=null) to status.yaml documents list."""

def update_extracted_data(claim_id, category, fields: Dict) -> None:
    """Merge fields into extracted_data.json under category key.
    For list-type categories (damage_photos, medical_receipts), append; do not overwrite."""

def get_extracted_data(claim_id) -> Dict:
    """Return full extracted_data.json as dict."""

def list_all_claims(status_filter=None, type_filter=None) -> List[Dict]:
    """Scan all claim folders. Return list of status.yaml contents."""

def save_summary(claim_id, text: str) -> None:
    """Write AI-generated summary.md to the claim folder."""
```

### 9.2 `storage.document_store` — Public API

```python
def save_document(claim_id, category, image_bytes, ext="jpg") -> str:
    """Save to {DATA_DIR}/claims/{claim_id}/documents/{category}_{timestamp}.{ext}.
    Returns filename only (not full path)."""

def get_document_bytes(claim_id, filename) -> bytes:
    """Read and return raw bytes of a stored document."""

def get_document_path(claim_id, filename) -> str:
    """Return full absolute path to a document file."""
```

### 9.3 `storage.sequence` — Public API

```python
def next_claim_id(claim_type: str) -> str:
    """Atomically increment counter for claim_type in sequence.json.
    Returns formatted Claim ID, e.g. 'CD-20260226-000013'."""
```

Thread-safe: uses `threading.Lock()` + `fcntl.flock(LOCK_EX)`.

---

## 10. Claim ID Sequence Generator

Format: `{type}-{YYYYMMDD}-{counter:06d}`

- `YYYYMMDD` = date the claim is **created** (not reformatted later)
- Counter is global (not per-day): CD goes `000001, 000002, ...` regardless of date
- CD and H have independent counters
- `sequence.json` seeded by `entrypoint.sh` on first run

```python
# storage/sequence.py (simplified)
import fcntl, json, threading, datetime, pathlib, os

DATA_DIR = os.getenv("DATA_DIR", "/data")
SEQUENCE_PATH = pathlib.Path(DATA_DIR) / "sequence.json"
_lock = threading.Lock()

def next_claim_id(claim_type: str) -> str:
    with _lock:
        with open(SEQUENCE_PATH, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            data = json.load(f)
            data[claim_type] = data.get(claim_type, 0) + 1
            f.seek(0); json.dump(data, f); f.truncate()
    today = datetime.date.today().strftime("%Y%m%d")
    return f"{claim_type}-{today}-{data[claim_type]:06d}"
```

---

## 11. Web Dashboards

All dashboards are **built** (`dashboards/reviewer.html`, `manager.html`, `admin.html`). Dashboard routes must be registered in `main.py` using **Jinja2** templates.

### 11.1 Reviewer Dashboard (`GET /reviewer`)

Three-panel layout:

| Panel | Content |
|---|---|
| **Left** | Claim list; search by ID; filter by status and type |
| **Centre** | Full-size document image + AI-extracted field table |
| **Right** | Document thumbnail grid for selected claim |

HTTP actions:

| Action | Endpoint | Storage call |
|---|---|---|
| Open claim | `GET /reviewer?claim_id=...` | `get_claim_status` + `get_extracted_data` |
| Serve document image | `GET /reviewer/document?claim_id=...&filename=...` | `get_document_bytes` |
| Mark Useful/Not Useful | `POST /reviewer/useful` `{claim_id, filename, useful}` | `mark_document_useful` |
| Save status + memo | `POST /reviewer/status` `{claim_id, status, memo}` | `update_claim_status` |

---

### 11.2 Manager Dashboard (`GET /manager`)

| Element | Calculation |
|---|---|
| Total Claims | `len(list_all_claims())` |
| Avg Response Time | Mean of all `metrics.response_times_ms` values across all claims |
| Accuracy Rate | `useful_true / (useful_true + useful_false) × 100` — only reviewed docs |
| Total Paid (CD) | Sum `metrics.total_paid_amount` for CD claims where `status == "Paid"` |
| Total Paid (H) | Same for H |
| Daily chart | Group `created_at[:10]` by date; split by type |

Filters: date range + claim type → query params → `list_all_claims`.

---

### 11.3 Admin Dashboard (`GET /admin`)

| Section | Detail |
|---|---|
| Log viewer | Read `/data/logs/app.log`; filter by level/date; max `LOG_MAX_MEMORY` (2000) entries |
| Log verbosity | `POST /admin/loglevel {level}` → `logging.getLogger().setLevel(level)` at runtime |
| AI token usage | Read `/data/token_records/YYYY-MM.jsonl`; group by operation; show total cost |

---

## 12. FastAPI Endpoints (Full)

| Method | Path | Handler | Description |
|---|---|---|---|
| `GET` | `/` | root | Version info (returns `{"status":"running","version":"2.0.0"}`) |
| `POST` | `/webhook` | webhook | LINE events; delegates to `_handle_webhook` |
| `POST` | `/callback` | callback | Alias of `/webhook` (both paths handled) |
| `GET` | `/health` | health_check | LINE + Gemini config status |
| `GET` | `/reviewer` | reviewer_dashboard | HTML dashboard |
| `GET` | `/reviewer/document` | reviewer_document | Serve raw image bytes |
| `POST` | `/reviewer/useful` | reviewer_useful | Mark document useful flag |
| `POST` | `/reviewer/status` | reviewer_status | Update claim status + memo |
| `GET` | `/manager` | manager_dashboard | HTML dashboard |
| `GET` | `/manager/data` | manager_data | JSON stats for chart/table |
| `GET` | `/admin` | admin_dashboard | HTML dashboard |
| `POST` | `/admin/loglevel` | admin_loglevel | Change log level at runtime |
| `GET` | `/admin/tokens` | admin_tokens | AI token usage JSON |

> ⚠️ Dashboard endpoints listed above are defined in the HTML files and spec. They must be registered as FastAPI routes in `main.py`.

### Webhook Security

The `_handle_webhook` helper in `main.py` enforces:
- Empty body → `400 Bad Request`
- Invalid HMAC-SHA256 signature → `400 Bad Request`
- Malformed JSON / missing `events` key / non-UTF-8 → `400 Bad Request` (not 500)

---

## 13. LINE Flex Message Components

All functions in `flex_messages.py`. Return `FlexContainer` via `FlexContainer.from_dict(...)`.

### Existing (v1.0 — in use)

| Function | Trigger state |
|---|---|
| `create_request_info_flex()` | Session start ("เช็คสิทธิ์เคลมด่วน") |
| `create_vehicle_selection_flex(policies)` | `waiting_for_vehicle_selection` — ⚠️ defined twice (L129 + L775); second definition wins |
| `create_policy_info_flex(policy_info)` | Policy found (CD) |
| `create_analysis_result_flex(...)` | Damage analysis done |
| `create_additional_info_prompt_flex()` | After damage photo received |
| `create_next_steps_flex()` | After analysis: "ส่งเคลม / จบการสนทนา" |
| `create_claim_submission_instructions_flex()` | When user chose "ส่งเคลม" |

### v2.0 New (built for `handlers/` package)

| Function | Trigger state | Status |
|---|---|---|
| `create_document_checklist_flex(claim_type, has_counterpart, uploaded_docs)` | After counterpart answer | ✅ Required by `handlers/documents.py` |
| `create_doc_received_flex(category, fields, still_missing)` | After each upload | ✅ Required by `handlers/documents.py` |
| `create_ownership_question_flex(extracted_name)` | `awaiting_ownership` | ✅ Required by `handlers/documents.py` |
| `create_submit_prompt_flex(claim_id, doc_count)` | `ready_to_submit` | ✅ Required by `handlers/documents.py` |
| `create_submission_confirmed_flex(claim_id)` | After `submitted` | ✅ Required by `handlers/submit.py` |
| `create_claim_type_selector_flex()` | Ambiguous trigger | ❌ Not yet built |
| `create_claim_confirmed_flex(claim_id, claim_type)` | Claim type confirmed | ❌ Not yet built |
| `create_health_policy_info_flex(policy_info)` | Health policy found | ❌ Not yet built |

### Bilingual Rule (FR-12.1)

Every message to the customer — both `TextMessage` strings and Flex Message text fields — **must contain Thai followed by English**. Pattern: Thai primary text, English sub-text or parenthetical.

---

## 14. Docker & Deployment

### `docker-compose.yml` (current)

```yaml
services:
  line-bot:
    build: .
    container_name: line-bot
    env_file: .env
    expose:
      - "8000"
    volumes:
      - claim-data:/data
    environment:
      - DATA_DIR=/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always

  ngrok:
    image: ngrok/ngrok:latest
    container_name: ngrok
    command: ["http", "line-bot:8000", "--log=stdout"]
    environment:
      - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
    ports:
      - "4040:4040"
    depends_on:
      line-bot:
        condition: service_healthy
    restart: always

  mock-chat:
    build: .
    container_name: mock-chat
    command: python mock_chat.py          # ❌ mock_chat.py does not exist yet
    env_file: .env
    environment:
      - LINE_API_HOST=http://mock-chat:8001
      - LINE_DATA_API_HOST=http://mock-chat:8001
      - BOT_URL=http://line-bot:8000
    ports:
      - "8001:8001"
    depends_on: [line-bot]
    restart: always
    profiles: [dev]

volumes:
  claim-data:
    driver: local
```

### `entrypoint.sh`

Handles on-container-start:
1. Optional `git pull` (if `REPO_URL` and `BRANCH` set)
2. Creates all `/data` subdirs (`claims/`, `logs/`, `token_records/`)
3. Seeds `sequence.json` on first run (`{"CD": 0, "H": 0}`)
4. `exec python /app/main.py`

### Running Tests

```bash
# Install test deps
pip install -r requirements_test.txt

# Run full suite (338 tests)
pytest tests/ -v

# Run by marker
pytest tests/ -m unit
pytest tests/ -m "flow_cd"
pytest tests/ -m security
```

Test markers (defined in `pytest.ini`):

| Marker | Description |
|---|---|
| `unit` | Pure unit tests (no I/O, no network) |
| `integration` | End-to-end through the FastAPI layer |
| `security` | Webhook security and signature verification |
| `slow` | Tests that may take > 2 s |
| `flow_cd` | Car Damage conversation flow |
| `flow_health` | Health conversation flow |

---

## 15. Non-Functional Requirements

### Performance Targets (BRD §10)

| Operation | Target | Note |
|---|---|---|
| Text reply | < 3 s | Immediate `reply_message`; push AI result async |
| AI OCR (identity photo) | < 10 s | Single Gemini vision call |
| Document categorisation | < 5 s | Simple class-detection prompt |
| Data extraction per doc | < 10 s | Structured JSON prompt |
| Damage analysis + verdict | < 30 s | Multi-modal: image + PDF |
| Dashboard page load | < 2 s | Static HTML + JSON; no AI calls |

### Security

| Requirement | Implementation |
|---|---|
| Webhook auth | `WebhookHandler` HMAC-SHA256; enforced in `_handle_webhook` |
| API keys | `.env` only — never in source code or logs; validated at startup in `config.py` |
| PII in logs | Log only: Claim IDs, doc categories, state names, error codes — **never** name, CID, or phone |
| AI file cleanup | `finally` block deletes Gemini uploaded files after every call |
| Dashboard auth | **Not in PoC**; required before production (JWT or session cookie) |

### Logging

- All modules use `logger = logging.getLogger(__name__)` — no `print()` calls.
- Configuration: `RotatingFileHandler` writing to `/data/logs/app.log`.
- Constants in `constants.py`:
  - `LOG_MAX_BYTES = 10 MB`
  - `LOG_BACKUP_COUNT = 7` (→ ~70 MB max)
  - `LOG_MAX_MEMORY = 2000` (max log entries in Admin dashboard memory)
- Every log entry must include: `timestamp | level | claim_id (if known) | operation | message`.

### Architecture Rules (Must Not Be Violated)

| Rule | Detail |
|---|---|
| **State is the only router** | First branch in any handler must always be on `session["state"]` |
| **All file I/O via `storage/`** | No code outside the `storage/` package reads or writes files in `/data` |
| **All AI calls via `ai/`** | No code outside the `ai/` package calls `genai.*` (exception: `claim_engine.py` for v1.0 flow, until replaced) |
| **Reply token used exactly once** | `reply_message()` must be called exactly once per webhook event |
| **Gemini files always deleted** | Every `genai.upload_file()` inside `try/finally` that calls `genai.delete_file()` |
| **No PII in logs** | Never log names, ID card numbers, phone numbers, or policy numbers |

---

## 16. Remaining Migration Steps

The following steps are **still required** to complete the v2.0 migration. Each step must leave the bot in a working state.

| Step | Change | Status |
|---|---|---|
| **A** | Create `mock_chat.py` | ❌ Blocker for `--profile dev` |
| **B** | Register dashboard routes in `main.py` (Jinja2 + all 12 endpoints) | ❌ Not done |
| **C** | Wire `handlers/trigger.py` + `handlers/identity.py` into `main.py` (replace v1.0 detect/verify states) | ❌ Not done |
| **D** | Wire `handlers/documents.py` into `handle_image_message` + `handle_text_message` (uploading/ownership states) | ❌ Not done |
| **E** | Wire `handlers/submit.py` into `handle_text_message` (`ready_to_submit` state) | ❌ Not done |
| **F** | Add Health (H) claim type support in `main.py`; add H policy records to `mock_data.py` | ❌ Not done |
| **G** | Fix `create_vehicle_selection_flex` duplicate in `flex_messages.py` (L129 vs L775) | ❌ Bug to fix |
| **H** | Build missing Flex components: `create_claim_type_selector_flex`, `create_claim_confirmed_flex`, `create_health_policy_info_flex` | ❌ Not done |
| **I** | Bilingual update — all TextMessage strings and Flex text fields | ❌ Not done |
| **J** | Wire token tracking into `main.py`/`claim_engine.py` (currently only in `ai/` package) | ❌ Not done |

> **Note on Steps C–E:** The v2.0 handler package (`handlers/trigger.py`, `handlers/identity.py`, `handlers/documents.py`, `handlers/submit.py`) is **fully implemented and tested**. The only remaining work is wiring them into `main.py` by replacing the v1.0 state branches.

---

## 17. Open Questions

| # | Question | Options | Default assumption |
|---|---|---|---|
| OQ-1 | Where do Health policy records come from? | (a) Add to `mock_data.py`, (b) Separate `health_policies.json` | Add to `mock_data.py` |
| OQ-2 | If Gemini miscategorises a document, does the user get to correct it? | (a) Accept AI verdict, (b) Show category + "Correct?" QuickReply | Accept AI verdict |
| OQ-3 | Dashboard authentication method? | JWT, Basic Auth, LINE Login for Business | No auth for PoC |
| OQ-4 | Maximum damage photos per claim? | 1 / 3 / unlimited | Unlimited (numbered `vehicle_damage_photo_1`, `_2`, ...) |
| OQ-5 | AI-generated `summary.md` — on submission or on Reviewer open? | On submission / On open | On submission (implemented in `handlers/submit.py`) |
| OQ-6 | GPS extraction — hard requirement or best-effort? | Hard / Best-effort (null if absent) | Best-effort |
| OQ-7 | Gemini token pricing constants — who provides values? | DevOps / Product Owner | Developer sets from current GA pricing page; overridable via env vars |

---

*Source documents: [business-requirement.md](business-requirement.md) · [user-journey.md](user-journey.md) · [document-verify.md](document-verify.md)*  
*Tech spec last updated: February 26, 2026 by Technical Lead (AI)*
