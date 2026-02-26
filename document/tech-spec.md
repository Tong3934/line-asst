# Technical Specification — LINE Insurance Claim Bot
## เช็คสิทธิ์ & เคลมประกันด่วน — v2.0

**Spec Version:** 2.0  
**BRD Reference:** [business-requirement.md](business-requirement.md) v2.0  
**User Journey Reference:** [user-journey.md](user-journey.md) v2.0  
**Last Updated:** February 2026  
**Authors:** Technical Development Team

---

## ⚠️ Current Implementation Gap

The existing codebase implements **BRD v1.0** (eligibility check only).  
**BRD v2.0** requires significant new functionality. This document describes **both** what exists and what must be built.

| Area | v1.0 (Exists) | v2.0 (Required — Build) |
|---|---|---|
| Claim types | Car Damage only | + Health (H) |
| Trigger | Single keyword only | Keyword detection from free text |
| Claim ID | None | `CD-YYYYMMDD-NNNNNN` / `H-YYYYMMDD-NNNNNN` |
| Identity verification | CID / plate / name text | + AI OCR from ID card / driving license photo |
| Document types | Damage photo only | 9 document types with per-type field extraction |
| Data extraction | Damage analysis (unstructured text) | Structured JSON per document type |
| Storage | In-memory sessions only | Persistent per-claim folder on Docker volume |
| Claim submission | Not implemented | Full submit + status lifecycle |
| Web dashboards | None | Reviewer, Manager, Admin |
| Language | Thai only | Thai + English (bilingual, every message) |
| AI token tracking | None | Per-call tracking, Admin dashboard |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Repository Structure (Target)](#3-repository-structure-target)
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
16. [Migration Notes — v1 → v2](#16-migration-notes--v1--v2)
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
| LINE Platform | `POST /webhook` | Webhook events |
| Health probe | `GET /health` | CI / monitoring |

---

## 2. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11 | Existing |
| Web framework | FastAPI | Existing |
| ASGI server | Uvicorn | Existing |
| LINE Bot SDK | `line-bot-sdk` v3 | Existing |
| AI | Google Gemini `models/gemini-2.5-flash` | Existing |
| Image processing | Pillow | Existing |
| HTTP client | httpx | Existing |
| Config | python-dotenv | Existing |
| YAML read/write | `pyyaml` | **Add to requirements.txt** |
| Web dashboard HTML | Jinja2 templates served by FastAPI | **New** |
| Containerisation | Docker + Docker Compose | Existing |
| Tunnelling (dev) | ngrok | Existing |
| Mock chat UI (dev) | `mock_chat.py` | Added in v1.1 |

---

## 3. Repository Structure (Target)

```
line-asst/
├── main.py                  # FastAPI app — bot handlers + dashboard endpoints
├── flex_messages.py         # All LINE Flex Message / QuickReply builders
├── mock_data.py             # Policy lookup — replace with DB in production
├── mock_chat.py             # Dev-only mock LINE platform UI
├── ngrok.py                 # Dev-only pyngrok tunnel launcher
│
├── handlers/                # NEW — one file per bot conversation topic
│   ├── __init__.py
│   ├── trigger.py           # Claim type detection, session init, Claim ID
│   ├── identity.py          # Policy verification (text + OCR path)
│   ├── documents.py         # Upload loop, categorisation, extraction, ownership
│   └── submit.py            # Completeness check + submission
│
├── ai/                      # NEW — all AI operations isolated here
│   ├── __init__.py
│   ├── categorise.py        # Categorise document image → type string
│   ├── extract.py           # Extract structured JSON from categorised image
│   ├── analyse_damage.py    # Eligibility verdict (existing, refactored)
│   └── ocr.py               # ID card / driving license OCR (existing, refactored)
│
├── storage/                 # NEW — all file I/O isolated here
│   ├── __init__.py
│   ├── claim_store.py       # Read/write status.yaml, extracted_data.json
│   ├── document_store.py    # Save/read document image files
│   └── sequence.py          # Claim ID counter (sequence.json)
│
├── dashboards/              # NEW — web dashboard HTML templates + routes
│   ├── reviewer.html
│   ├── manager.html
│   └── admin.html
│
├── requirements.txt         # + pyyaml, jinja2
├── dockerfile
├── docker-compose.yml       # + /data volume mount
├── entrypoint.sh
├── nginx.conf
├── .env.example
├── .gitignore
│
└── document/
    ├── tech-spec.md         # This file
    ├── business-requirement.md
    ├── user-journey.md
    └── document-verify.md
```

---

## 4. Environment Variables

All variables loaded from `.env` via `python-dotenv`. Copy `.env.example` → `.env`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | — | LINE Messaging API access token |
| `LINE_CHANNEL_SECRET` | ✅ | — | LINE webhook signature secret |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `NGROK_AUTHTOKEN` | ✅ (Docker) | — | ngrok tunnel auth token |
| `PORT` | ❌ | `8000` | Uvicorn listen port |
| `DATA_DIR` | ❌ | `/data` | Root path for the persistent volume |
| `LINE_API_HOST` | ❌ | `https://api.line.me` | Override to `http://localhost:8001` for mock testing |
| `LINE_DATA_API_HOST` | ❌ | `https://api-data.line.me` | Override to `http://localhost:8001` for mock testing |
| `BOT_URL` | ❌ | `http://localhost:8000` | Used by `mock_chat.py` to reach the bot |
| `REPO_URL` | ❌ | — | Git repo URL (auto-pull via `entrypoint.sh`) |
| `BRANCH` | ❌ | — | Git branch for auto-pull |

---

## 5. Data Models

### 5.1 Session (`user_sessions` dict — in-memory)

```python
user_sessions: Dict[str, Dict] = {
    "<line_user_id>": {
        # ── Core state ──
        "state":           str,          # See §6 for all valid states
        "claim_id":        str,          # e.g. "CD-20260226-000001"
        "claim_type":      str,          # "CD" | "H"

        # ── Policy (set after verification) ──
        "policy_info":     Dict,         # Full policy record from storage

        # ── Car Damage specific ──
        "has_counterpart": str | None,   # "มีคู่กรณี" | "ไม่มีคู่กรณี"
        "search_results":  List[Dict],   # Populated only in vehicle-selection state

        # ── Document tracking ──
        "uploaded_docs":   Dict[str, str],  # {doc_category: filename}
        "awaiting_ownership_for": str | None,  # temp filename pending ownership confirm

        # ── Optional ──
        "additional_info": str | None,   # Free-text incident description
    }
}
```

**State is the single source of truth** for routing every incoming message or image.
Do NOT branch on any field other than `state` to decide how to respond.

---

### 5.2 Policy Record

Two flavours — Car Damage and Health. Both stored as Python dicts (PoC: from `mock_data.py`; Production: from DB/API).

**Car Damage Policy:**

```python
{
    "policy_number":          str,   # "CD-2026-001234"
    "id_card_number":         str,   # 13-digit string (no dashes)
    "title_name":             str,   # "นาย" | "นาง" | "นางสาว"
    "first_name":             str,   # strip() before use — may have trailing space
    "last_name":              str,
    "phone":                  str,
    "vehicle_plate":          str,
    "vehicle_brand":          str,
    "vehicle_model":          str,
    "vehicle_year":           str,
    "vehicle_color":          str,
    "coverage_type":          str,   # "ชั้น 1" | "ชั้น 2+" | "ชั้น 2" | "ชั้น 3+" | "ชั้น 3"
    "coverage_amount":        int,   # THB
    "deductible":             int,   # THB (ค่าเสียหายส่วนแรก)
    "insurance_company":      str,
    "policy_start":           str,   # "YYYY-MM-DD"
    "policy_end":             str,   # "YYYY-MM-DD"
    "status":                 str,   # "active" | "expired" | "inactive"
    "policy_document_base64": str | None,  # PDF for damage analysis AI prompt
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
  status.yaml             ← claim metadata (see 5.4)
  extracted_data.json     ← all AI field extractions (see 5.5)
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
  - category: "vehicle_damage_photo"
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
  "damage_photos": [
    {
      "filename": "vehicle_damage_photo_1_20260226_120030.jpg",
      "damage_location": "ประตูซ้ายหน้า",
      "damage_description": "รอยบุบและรอยขูดขีด",
      "severity": "moderate",
      "gps_lat": 13.7563,
      "gps_lon": 100.5018
    }
  ],
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
  "medical_receipts": [
    {
      "filename": "receipt_1_20260226_130000.jpg",
      "hospital_name": "...", "billing_number": "...",
      "total_paid": 4500, "date": "...",
      "items": [{"description": "...", "amount": 4500}]
    }
  ]
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
- **Must survive container restarts** — mounted on the persistent volume.
- Format: `{type}-{YYYYMMDD}-{counter:06d}` → `CD-20260226-000013`

---

### 5.7 Claim Status Lifecycle

```
Submitted → Under Review → Pending → Approved → Paid
                         ↘
                          Rejected
```

Valid transitions enforced in the Reviewer dashboard save handler:

| From | Allowed next values |
|---|---|
| Submitted | Under Review |
| Under Review | Pending, Approved, Rejected |
| Pending | Under Review, Rejected |
| Approved | Paid |

---

## 6. Conversation State Machine

Each user session is identified by their LINE `user_id`. The active state is always in `user_sessions[user_id]["state"]`.

### Full State Diagram

```
                  ┌────────────────────────────────────────────────────────────────┐
                  │  Cancel keywords ("ยกเลิก","cancel","เริ่มใหม่") from any state │
                  ▼                                                                │
              [idle]                                                               │
                  │ CD/H keyword or "เช็คสิทธิ์เคลมด่วน" detected                 │
                  ▼                                                                │
          [detecting_claim_type]                                                   │
                  │ CD or H confirmed                                              │
                  ▼                                                                │
          [verifying_policy]  ◄── retry if not found / expired                    │
                  │ Policy found                                                   │
         ┌────────┴────────┐                                                       │
         │ CD              │ H                                                     │
         ▼                 └──────────────────────────┐                           │
  [waiting_for_counterpart]                           │                           │
         │ Answered (or single policy auto-selected)  │                           │
         ▼                                            ▼                           │
  [uploading_documents] ◄─────────────── [uploading_documents]                   │
         │                                                                        │
         │  Driving license received (CD with-counterpart only)                  │
         ▼                                                                        │
  [awaiting_ownership]                                                            │
         │ Ownership confirmed                                                    │
         ▼                                                                        │
  [uploading_documents]  ◄── loop until all required docs received                │
         │ All docs complete                                                       │
         ▼                                                                        │
  [ready_to_submit]                                                               │
         │ Customer taps Submit                                                   │
         ▼                                                                        │
     [submitted] ────────────────────────────────────────────────────────────────┘
```

### State Transition Table

| State | Input | Next State | Bot Action |
|---|---|---|---|
| `idle` | CD keywords in free text | `detecting_claim_type` | Confirm "Car Damage"; show Claim ID |
| `idle` | H keywords in free text | `detecting_claim_type` | Confirm "Health claim"; show Claim ID |
| `idle` | Ambiguous / both keyword sets | `idle` | Ask "🚗 ประกันรถ or 🏥 ประกันสุขภาพ?" |
| `idle` | "เช็คสิทธิ์เคลมด่วน" | `detecting_claim_type` | Show claim type selector QuickReply |
| `detecting_claim_type` | "ประกันรถ" / car button | `verifying_policy` | Generate CD Claim ID; ask for CID |
| `detecting_claim_type` | "ประกันสุขภาพ" / health button | `verifying_policy` | Generate H Claim ID; ask for CID |
| `verifying_policy` | Text: 13-digit CID | next or retry | Look up policy; on match → show policy card |
| `verifying_policy` | Image: ID card or DL | next or retry | OCR → look up by extracted CID |
| `verifying_policy` | Multiple policies found | `waiting_for_vehicle_selection` | Carousel of vehicles |
| `waiting_for_vehicle_selection` | "เลือกทะเบียน {plate}" | `waiting_for_counterpart` (CD) | Show policy card + counterpart QuickReply |
| `waiting_for_counterpart` | "มีคู่กรณี" | `uploading_documents` | Show document checklist |
| `waiting_for_counterpart` | "ไม่มีคู่กรณี" | `uploading_documents` | Show document checklist (no counterpart DL) |
| `uploading_documents` | Image | `awaiting_ownership` or `uploading_documents` | Categorise → extract → confirm + progress |
| `uploading_documents` | Text | `uploading_documents` | "📷 Please send a photo" |
| `awaiting_ownership` | "ของฉัน (ฝ่ายเรา)" | `uploading_documents` | Assign `driving_license_customer`; update checklist |
| `awaiting_ownership` | "คู่กรณี (อีกฝ่าย)" | `uploading_documents` | Assign `driving_license_other_party`; update checklist |
| `uploading_documents` | All required docs uploaded | `ready_to_submit` | Summary card + Submit button |
| `ready_to_submit` | "ส่งคำร้อง" / "Submit" | `submitted` | Set status.yaml; push Claim ID confirmation |
| `submitted` | Any | `submitted` | Show Claim ID; offer to start new |
| Any | Cancel keyword | `idle` | "Session cancelled / ยกเลิกแล้ว. Send a message to start new." |

### Required Documents Per Claim Type

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

---

## 7. LINE Bot — Message Handlers

### 7.1 Text Message Handler (`handle_text_message`)

Evaluate branches **in order** — first match wins:

```
1. Cancel keyword?                      → clear session; state = "idle"; send cancel ack
2. state == "idle"                      → run claim-type keyword detection (FR-01.2 – FR-01.5)
3. state == "detecting_claim_type"      → handle clarification button press
4. state == "verifying_policy"          → policy lookup by typed 13-digit CID or name
5. state == "waiting_for_vehicle_selection" → handle "เลือกทะเบียน {plate}"
6. state == "waiting_for_counterpart"   → record has_counterpart; advance state
7. state == "awaiting_ownership"        → assign driving license side; advance state
8. state == "uploading_documents"       → send "📷 กรุณาส่งรูปภาพ / Please send a photo"
9. state == "ready_to_submit"           → handle "ส่งคำร้อง" trigger
10. state == "submitted"               → Claim ID reminder message
11. default                            → welcome + "ส่งข้อความเพื่อเริ่มต้น / Send a message to start"
```

**Claim-type keyword lists (FR-01.3 / FR-01.4):**

```python
CD_KEYWORDS = ["รถ","ชน","เฉี่ยว","ขโมย","หาย","car","vehicle","accident","damage","crash"]
H_KEYWORDS  = ["เจ็บ","ป่วย","ผ่าตัด","โรงพยาบาล","health","sick","hospital","medical","surgery"]
```

If both sets yield at least one match → ambiguous → ask user to clarify.

---

### 7.2 Image Message Handler (`handle_image_message`)

```
1. If state not in ["verifying_policy", "uploading_documents"]:
   → reply "⚠️ Please complete previous steps first / กรุณาทำตามขั้นตอนก่อนส่งรูป"
   → return

2. Send immediate reply_message acknowledgement (consumes the reply token):
   state == "verifying_policy" → "⏳ กำลังค้นหา... / Searching..."
   state == "uploading_documents" → "⏳ กำลังวิเคราะห์... / Analysing (10–30s)..."

3. Download image from LINE Data API:
   GET {_line_data_api_host}/v2/bot/message/{message_id}/content
   Authorization: Bearer {LINE_CHANNEL_ACCESS_TOKEN}

4. Branch: state == "verifying_policy"
   → ai.ocr.extract_id_from_image(image_bytes)
   → If type=="id_card"      → search_policies_by_cid(value)
   → If type=="license_plate"→ search_policies_by_plate(value)
   → If unknown              → push "❌ ไม่พบข้อมูลในรูปภาพ กรุณาลองใหม่"
   → Call process_search_result(..., use_push=True)

5. Branch: state == "uploading_documents"
   a. category = ai.categorise.categorise_document(image_bytes)
   b. If category == "unknown":
      → push "❌ ไม่รู้จักเอกสาร / Unknown document. Please send one of: {required list}"
      → return

   c. fields = ai.extract.extract_fields(image_bytes, category)

   d. If driving license AND has_counterpart == "มีคู่กรณี":
      → store temp image bytes in session["awaiting_ownership_for"]
      → state = "awaiting_ownership"
      → push ownership QuickReply (create_ownership_question_flex)
      → return

   e. filename = storage.document_store.save_document(claim_id, category, image_bytes)
   f. storage.claim_store.update_extracted_data(claim_id, category, fields)
   g. Mark uploaded_docs[category] = filename in session
   h. storage.claim_store update document list in status.yaml
   i. missing = check_missing_docs(session)
   j. push create_doc_received_flex(category, fields, missing)
   k. If not missing:
      → state = "ready_to_submit"
      → push create_submit_prompt_flex(claim_id, doc_count)
```

---

## 8. AI Integration (Google Gemini)

All Gemini calls share a wrapper that:
- Records token usage (prompt + completion tokens) → `/data/token_records/YYYY-MM.jsonl`
- Catches `429 Resource Exhausted` → returns user-friendly retry message
- Deletes any uploaded Gemini files in a `finally` block

### 8.1 `ai.ocr.extract_id_from_image(image_bytes) → Dict`

**Existing** `extract_info_from_image_with_gemini` — rename and move to `ai/ocr.py`.

- Returns `{"type": "id_card"|"license_plate"|"unknown", "value": str|None}`

---

### 8.2 `ai.categorise.categorise_document(image_bytes) → str`

**New.** Single Gemini vision call.

Valid return values (exact strings, enforced in code):

```
driving_license          vehicle_registration     citizen_id_card
receipt                  medical_certificate      itemised_bill
discharge_summary        vehicle_damage_photo     vehicle_location_photo
unknown
```

If response is not in the above set → treat as `"unknown"`.

---

### 8.3 `ai.extract.extract_fields(image_bytes, category) → Dict`

**New.** Different prompt per category. All prompts must:

1. **Buddhist Era conversion (BR-02):** Thai documents use พ.ศ. — instruct AI: "Convert all dates from Buddhist Era to Gregorian by subtracting 543. Return all dates as YYYY-MM-DD."
2. **Null for unreadable fields (FR-04.3):** "If a field cannot be read clearly, return null. Never guess."
3. **GPS extraction:** For `vehicle_damage_photo` and `vehicle_location_photo`, extract GPS decimal degrees from EXIF before calling Gemini:
   ```python
   # Extract EXIF GPS before the AI call
   from PIL import Image as PILImage
   from PIL.ExifTags import TAGS, GPSTAGS
   img = PILImage.open(io.BytesIO(image_bytes))
   exif = img._getexif() or {}
   gps = _parse_gps_exif(exif)   # returns (lat, lon) or (None, None)
   ```
   Pass GPS into the fields dict directly; do not ask Gemini to read EXIF.
4. **JSON only:** "Return only valid JSON. No markdown, no prose."

Returns a dict matching the schema in §5.5. On error returns `{}` with all keys as `null`.

---

### 8.4 `ai.analyse_damage.analyse_damage(...)` → str

**Existing** `analyze_damage_with_gemini` — move to `ai/analyse_damage.py`, no logic changes.

Every response MUST end with:
> *"การประเมินนี้เป็นเพียงการประเมินเบื้องต้นโดย AI / This is a preliminary AI assessment. Please confirm with your insurance company."*

Eligibility logic (embed in prompt):

| Insurance Class | ไม่มีคู่กรณี | มีคู่กรณี |
|:---:|:---:|:---:|
| ชั้น 1 | ✅ | ✅ |
| ชั้น 2+ / ชั้น 2 | ❌ | ✅ |
| ชั้น 3+ / ชั้น 3 | ❌ | ✅ |

---

### 8.5 Gemini File Upload Pattern

Used only in `analyse_damage`. Always clean up in `finally`:

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

Define token pricing constants in a `constants.py` file so they can be updated without code changes.

---

## 9. Storage Layer

All file I/O is isolated in `storage/`. No code outside this package reads or writes files directly.

### 9.1 `storage.claim_store` — Public API

```python
def create_claim(claim_id, claim_type, line_user_id, has_counterpart) -> None:
    """Create folder, empty extracted_data.json, initial status.yaml."""

def get_claim_status(claim_id) -> Dict:
    """Read and return status.yaml as dict."""

def update_claim_status(claim_id, status, memo=None, paid_amount=None) -> None:
    """Update status (and optionally memo/paid_amount) in status.yaml."""

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
    Returns formatted Claim ID, e.g. "CD-20260226-000013"."""
```

Thread-safe: use `threading.Lock()` + `fcntl.flock` (see §10 for implementation).

---

## 10. Claim ID Sequence Generator

Format: `{type}-{YYYYMMDD}-{counter:06d}`

- `YYYYMMDD` = date the claim is **created** (not reformatted later)
- Counter is global (not per-day): CD goes `000001, 000002, ...` regardless of date
- CD and H have independent counters

```python
import fcntl, json, threading, datetime, pathlib, os

DATA_DIR = os.getenv("DATA_DIR", "/data")
SEQUENCE_PATH = pathlib.Path(DATA_DIR) / "sequence.json"
_lock = threading.Lock()

def _ensure_sequence_file():
    if not SEQUENCE_PATH.exists():
        SEQUENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SEQUENCE_PATH.write_text(json.dumps({"CD": 0, "H": 0}))

def next_claim_id(claim_type: str) -> str:
    _ensure_sequence_file()
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

All dashboards served by the same FastAPI app using **Jinja2** templates.

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

Filters: date range + claim type → query params → re-query `list_all_claims`.

---

### 11.3 Admin Dashboard (`GET /admin`)

| Section | Detail |
|---|---|
| Log viewer | Read `/data/logs/app.log`; filter by level/date; max 2000 entries in memory |
| Log verbosity | `POST /admin/loglevel {level}` → `logging.getLogger().setLevel(level)` at runtime |
| AI token usage | Read `/data/token_records/YYYY-MM.jsonl`; group by operation; show total cost |

---

## 12. FastAPI Endpoints (Full)

| Method | Path | Handler | Description |
|---|---|---|---|
| `GET` | `/` | root | Version info |
| `POST` | `/webhook` | webhook | LINE events; verify HMAC-SHA256 |
| `GET` | `/health` | health_check | Line + Gemini config status |
| `GET` | `/reviewer` | reviewer_dashboard | HTML dashboard |
| `GET` | `/reviewer/document` | reviewer_document | Serve raw image bytes |
| `POST` | `/reviewer/useful` | reviewer_useful | Mark document useful flag |
| `POST` | `/reviewer/status` | reviewer_status | Update claim status + memo |
| `GET` | `/manager` | manager_dashboard | HTML dashboard |
| `GET` | `/manager/data` | manager_data | JSON stats for chart/table |
| `GET` | `/admin` | admin_dashboard | HTML dashboard |
| `POST` | `/admin/loglevel` | admin_loglevel | Change log level at runtime |
| `GET` | `/admin/tokens` | admin_tokens | AI token usage JSON |

---

## 13. LINE Flex Message Components

All functions in `flex_messages.py`. Return `FlexContainer` via `FlexContainer.from_dict(...)`.

### Existing (review for bilingual update)

| Function | Trigger | Update |
|---|---|---|
| `create_request_info_flex()` | Session start (current v1 pattern; replaced by claim-type flow in v2) | Consider deprecating |
| `create_vehicle_selection_flex(policies)` | Multiple policies found | Add EN subtitle |
| `create_policy_info_flex(policy_info)` | CD policy found | Add `coverage_amount`, `deductible` fields |
| `create_analysis_result_flex(...)` | Damage analysis done | Add disclaimer line |
| `create_additional_info_prompt_flex()` | After counterpart question | Repurpose as optional incident description step |

### New (must build)

| Function | Trigger | Content |
|---|---|---|
| `create_claim_type_selector_flex()` | Ambiguous trigger or "เช็คสิทธิ์" | QuickReply: "🚗 ประกันรถ / Car" · "🏥 ประกันสุขภาพ / Health" |
| `create_claim_confirmed_flex(claim_id, claim_type)` | Claim type confirmed | Shows Claim ID + type in both languages |
| `create_document_checklist_flex(claim_type, has_counterpart, uploaded_docs)` | After counterpart answer (CD) or policy shown (H) | Required docs list with ✅/⏳ per item; updates every upload |
| `create_doc_received_flex(category, extracted_fields, still_missing)` | After each successful upload | Confirms category, extracted key fields (table), remaining docs |
| `create_ownership_question_flex(extracted_name)` | Driving license uploaded (CD with-counterpart) | Name from extraction + QuickReply: "ของฉัน (ฝ่ายเรา)" · "คู่กรณี (อีกฝ่าย)" |
| `create_submit_prompt_flex(claim_id, doc_count)` | All docs complete | Summary card + "ส่งคำร้อง / Submit Claim" button |
| `create_submission_confirmed_flex(claim_id)` | Successful submission | Claim ID in large text; instructions to save it |
| `create_health_policy_info_flex(policy_info)` | Health policy found | Plan name, IPD/OPD coverage, room per night |

### Bilingual Rule (FR-12.1)

Every message to the customer — both inline `TextMessage` strings and all Flex Message text fields — **must contain Thai followed by English**. Suggested pattern:

```
Primary text (Thai)
Sub-text or parenthetical (English)
```

---

## 14. Docker & Deployment

### Updated `docker-compose.yml`

```yaml
services:
  line-bot:
    build: .
    container_name: line-bot
    env_file: .env
    expose:
      - "8000"
    volumes:
      - claim-data:/data         # REQUIRED for v2
    environment:
      - DATA_DIR=/data
    restart: always

  ngrok:
    image: ngrok/ngrok:latest
    container_name: ngrok
    command: ["http", "line-bot:8000", "--log=stdout"]
    environment:
      - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
    ports:
      - "4040:4040"
    depends_on: [line-bot]
    restart: always

  mock-chat:
    build: .
    container_name: mock-chat
    command: python mock_chat.py
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

### `requirements.txt` Additions

```
pyyaml
jinja2
```

### Application Startup Checks

Add to `main.py` before `uvicorn.run(...)`:

```python
import pathlib, json

def _init_data_dir():
    data = pathlib.Path(os.getenv("DATA_DIR", "/data"))
    (data / "claims").mkdir(parents=True, exist_ok=True)
    (data / "logs").mkdir(parents=True, exist_ok=True)
    (data / "token_records").mkdir(parents=True, exist_ok=True)
    seq = data / "sequence.json"
    if not seq.exists():
        seq.write_text(json.dumps({"CD": 0, "H": 0}))
```

---

## 15. Non-Functional Requirements

### Performance Targets (BRD §10)

| Operation | Target | Note |
|---|---|---|
| Text reply | < 3 s | Immediate `reply_message`; push result async |
| AI OCR (identity photo) | < 10 s | Single Gemini vision call |
| Document categorisation | < 5 s | Simple class-detection prompt |
| Data extraction per doc | < 10 s | Structured JSON prompt; varies by doc complexity |
| Damage analysis + verdict | < 30 s | Multi-modal: image + PDF |
| Dashboard page load | < 2 s | Static HTML + JSON; no AI calls |

### Security

| Requirement | Implementation |
|---|---|
| Webhook auth | `WebhookHandler` HMAC-SHA256 (existing) |
| API keys | `.env` only — never in source code or logs |
| PII in logs | Log only Claim IDs, doc categories, and error codes — **never** name, CID, or phone |
| AI file cleanup | `finally` block deletes Gemini uploaded files after every call (existing pattern) |
| Dashboard auth | **Not in PoC**; required before production (JWT or session cookie) |

### Logging

- Replace all `print()` calls with `logging.getLogger(__name__)`.
- Write to `/data/logs/app.log` with `RotatingFileHandler` (7-day / 2000 entries max).
- Every log entry includes: `timestamp | level | claim_id (if known) | operation | message`.

---

## 16. Migration Notes — v1 → v2

Implement in this order to maintain a working bot at each step:

| Step | Change | Risk if skipped |
|---|---|---|
| **1** | Add `pyyaml`, `jinja2` to `requirements.txt`; add volume to docker-compose; add `DATA_DIR` env var | Steps 2+ cannot run |
| **2** | Create `storage/` package; implement `sequence.py` and `claim_store.py` | No claim IDs or persistence |
| **3** | Show Claim ID in existing policy-found flow (CD only); call `create_claim` on policy match | No Claim ID in early messages |
| **4** | Add `ai/categorise.py` + `ai/extract.py`; replace single-purpose image handler with multi-doc pipeline | Only damage photos work |
| **5** | Add `"ready_to_submit"` state + `create_submit_prompt_flex` + submit handler | No submission flow |
| **6** | Add Health (H) claim type; update `mock_data.py`; add `create_health_policy_info_flex` | Health claims unsupported |
| **7** | Build Reviewer, Manager, Admin dashboards | No internal visibility |
| **8** | Bilingual update — all Flex Messages and TextMessage strings | FR-12.1 not met |
| **9** | Token tracking (append to `/data/token_records/`) | Admin AI cost view unavailable |
| **10** | Replace `print()` with `logging`; write to `/data/logs/` | Admin log view unavailable |

---

## 17. Open Questions

The following decisions need input before implementation begins. Defaults shown are what the developer should assume if no answer is received within 2 working days.

| # | Question | Options | Default assumption |
|---|---|---|---|
| OQ-1 | Where do Health policy records come from? | (a) Add to `mock_data.py`, (b) Separate `health_policies.json` | Add to `mock_data.py` |
| OQ-2 | If Gemini miscategorises a document, does the user get to correct it? | (a) Accept AI verdict only, (b) Show category + "Correct?" QuickReply | Accept AI verdict |
| OQ-3 | Dashboard authentication method? | JWT, Basic Auth, LINE Login for Business | No auth for PoC |
| OQ-4 | Maximum damage photos per claim? | 1 / 3 / unlimited | Unlimited |
| OQ-5 | AI-generated `summary.md` — on submission or on Reviewer open? | On submission / On open | On submission |
| OQ-6 | GPS extraction — hard requirement or best-effort? | Hard / Best-effort (null if absent) | Best-effort |
| OQ-7 | Gemini token pricing constants — who provides values? | DevOps / Product Owner | Developer to set from current GA pricing page |

---

*Source documents: [business-requirement.md](business-requirement.md) · [user-journey.md](user-journey.md) · [document-verify.md](document-verify.md)*
