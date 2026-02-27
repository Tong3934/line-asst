# Senior AI Developer — Identity & Handover Document

> **Purpose:** This document describes the AI agent that built and maintains the
> LINE Insurance Claim Bot v2.0. Pass this file to the next AI agent or senior
> developer so they can continue the work without re-reading every source file.

---

## 1. Role & Identity

| Field | Value |
|---|---|
| **Role title** | Senior Software Developer (AI Agent) |
| **Alias** | GitHub Copilot (Claude Sonnet 4.6 under the hood) |
| **Specialisations** | Python 3.11+, FastAPI, LINE Bot SDK v3, Google Gemini AI, Docker / Docker Compose, 12-Factor microservice design, pytest, Jinja2, YAML/JSON storage, Kubernetes migration preparation |
| **Working language** | English (code) + Thai/English bilingual output for end-users |
| **Date of last session** | 2026-02-26 (code quality review + fixes) |
| **Git branch** | `add_doc_verify` |

---

## 2. Project Overview

**Repository:** `/Users/80012735/NTL-GHE/line-asst`  
**Application name:** LINE Insurance Claim Bot  
**Current version:** `2.0.0` (defined in `constants.py → APP_VERSION`)  
**Runtime:** Python 3.11 on Docker; Python 3.14 in local venv (`.venv/`)

### What the bot does
A LINE Messaging chatbot that lets insurance customers file claims through
LINE chat. The bot supports two claim types:

| Code | Type | Key workflow |
|---|---|---|
| **CD** | Car Damage | Trigger → policy lookup by CID/plate/name → has counterpart? → upload 3–4 documents → AI categorisation + extraction → submit |
| **H** | Health | Trigger → policy lookup by CID → upload 4 documents → AI categorisation + extraction → submit |

### External services used
| Service | Purpose | SDK / lib |
|---|---|---|
| LINE Messaging API | Webhook receive + reply/push | `linebot.v3` (SDK v3) |
| LINE Data API | Download images sent by users | `httpx` direct HTTP |
| Google Gemini `models/gemini-2.5-flash` | OCR, document categorisation, field extraction, damage analysis | `google.generativeai` |

---

## 3. Architecture & 12-Factor Compliance

The codebase is designed for easy migration from Docker sandbox → Kubernetes.

| 12-Factor principle | Implementation |
|---|---|
| **III – Config** | All secrets + tunable values in env vars (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `GEMINI_API_KEY`, `DATA_DIR`, `LINE_API_HOST`, `LINE_DATA_API_HOST`, `LOG_LEVEL`, etc.). See `.env.example`. |
| **VI – Stateless** | In-memory `user_sessions` dict; all durable state on `/data` volume (maps to a Kubernetes PVC). |
| **VII – Port binding** | Uvicorn binds `:8000`. `PORT` env var overrides. |
| **IX – Disposability** | `asynccontextmanager` lifespan, SIGTERM handled by Uvicorn. `entrypoint.sh` creates dirs before exec. |
| **XI – Logs as streams** | `logging.handlers.RotatingFileHandler` → `/data/logs/app.log` + stdout `StreamHandler`. Level overridable at runtime via `POST /admin/loglevel`. |

### Directory layout

```
/Users/80012735/NTL-GHE/line-asst/
│
├── main.py                    # FastAPI app, webhook router, dashboard routes
├── constants.py               # All app-wide constants (no secrets)
├── mock_data.py               # In-process mock policy database (CD + H)
├── flex_messages.py           # All LINE Flex Message builders
├── ngrok.py                   # Local tunnel helper (dev only)
│
├── ai/
│   ├── __init__.py            # Shared Gemini client (_model), call_gemini(), token tracking
│   ├── ocr.py                 # extract_id_from_image() → {type, value}
│   ├── categorise.py          # categorise_document() → category string | "unknown"
│   ├── extract.py             # extract_fields() → Dict per category
│   └── analyse_damage.py      # analyse_damage() → bilingual eligibility text
│
├── handlers/
│   ├── __init__.py
│   ├── trigger.py             # is_trigger(), handle_trigger(), handle_claim_type_selection()
│   ├── identity.py            # handle_policy_text(), handle_policy_image(), handle_vehicle_selection()
│   ├── documents.py           # handle_counterpart_answer(), handle_ownership_answer(), handle_document_image()
│   └── submit.py              # handle_submit_request()
│
├── storage/
│   ├── __init__.py
│   ├── sequence.py            # next_claim_id(claim_type) → "CD-20260226-000001"
│   ├── claim_store.py         # Full CRUD on /data/claims/{claim_id}/status.yaml + extracted_data.json
│   └── document_store.py      # save_document(), get_document_bytes(), list_documents()
│
├── dashboards/                # Jinja2 HTML templates served by FastAPI
│   ├── reviewer.html          # FR-08: Document review + status transitions
│   ├── manager.html           # FR-09: KPI cards + Chart.js charts
│   └── admin.html             # FR-10: Log level, token usage, health
│
├── tests/
│   ├── conftest.py            # Fixtures: app_client, mock_line_api, mock_gemini, mock_policy_lookup, set_session, get_session
│   ├── test_data.py           # Shared constants: sample policies, webhook payloads, OCR/AI stubs
│   ├── test_api_endpoints.py  # TC-ENDPOINT-01..05: GET /, /health, POST /webhook, /reviewer, /admin
│   ├── test_business_logic.py # TC-BL-01..10: state machine, keyword detection, phone extraction, signature
│   ├── test_conversation_flows.py  # TC-FLOW-01..09: full end-to-end webhook flows via TestClient
│   └── test_webhook_security.py    # HMAC verification, malformed payloads, PII safety
│
├── document/
│   ├── business-requirement.md   # BRD v2.0 (source of truth for features)
│   ├── tech-spec.md              # Technical spec v2.0 (architecture, API, storage schema)
│   ├── document-verify.md        # Alternate tech spec variant (Azure OpenAI flavour)
│   └── user-journey.md           # LINE user journey maps
│
├── docker-compose.yml         # Production + dev (mock-chat profile) services
├── dockerfile                 # Multistage build; EXPOSE 8000; VOLUME ["/data"]
├── entrypoint.sh              # mkdir /data/**; seed sequence.json; exec python main.py
├── requirements.txt           # All packages pinned
├── .env.example               # Documents every env var (no real values)
└── .biology/
    └── SrDev.md               # ← this file
```

---

## 4. Session State Machine

`user_sessions[user_id]` schema:

```python
{
    "state":                  str,   # see state list below
    "claim_id":               str | None,
    "claim_type":             "CD" | "H" | None,
    "policy_info":            dict | None,   # from mock_data
    "has_counterpart":        "มีคู่กรณี" | "ไม่มีคู่กรณี" | None,
    "search_results":         list[dict],   # multiple policy hits
    "uploaded_docs":          dict,         # {storage_key: filename}
    "awaiting_ownership_for": dict | None,  # {filename, fields, image_bytes}
    "additional_info":        str | None,
}
```

State values and routing (in `main.py → handle_text_message`):

| State | Meaning | Handler called |
|---|---|---|
| `idle` | Fresh session | `is_trigger()` check → `handle_trigger()` |
| `detecting_claim_type` | Trigger fired but claim type ambiguous | `handle_claim_type_selection()` |
| `verifying_policy` / `waiting_for_info` | Waiting for CID/plate/name/image | `handle_policy_text()` / `handle_policy_image()` |
| `waiting_for_vehicle_selection` | Multiple policies found | `handle_vehicle_selection()` |
| `waiting_for_counterpart` | CD only: has counterpart? | `handle_counterpart_answer()` |
| `uploading_documents` | Accepting document images | `handle_document_image()` |
| `awaiting_ownership` | Driving license: customer or other party? | `handle_ownership_answer()` |
| `ready_to_submit` | All required docs received | Submit trigger or continue uploading |
| `submitted` | Claim submitted | Informational reply only |

> **Important:** Tests seed sessions using **both** `"verifying_policy"` and
> `"waiting_for_info"`. `main.py` accepts both (added `or "waiting_for_info"` in
> the routing conditions).

---

## 5. Storage Schema

### `/data/claims/{claim_id}/status.yaml`

```yaml
claim_id:   CD-20260226-000013
claim_type: CD
status:     Submitted          # see VALID_TRANSITIONS in constants.py
policy_no:  POL-2024-001234
user_id:    Uxxxxxxxxxxxxxxx
created_at: "2026-02-26T10:00:00+00:00"
updated_at: "2026-02-26T10:05:00+00:00"
has_counterpart: มีคู่กรณี
documents:
  - filename: driving_license_customer_20260226_100100.jpg
    category: driving_license_customer
    useful: true
  - filename: vehicle_registration_20260226_100200.jpg
    category: vehicle_registration
    useful: null
memo: ""
paid_amount: null
```

### `/data/claims/{claim_id}/extracted_data.json`

```json
{
  "driving_license_customer": { "full_name_th": "สมชาย ใจดี", "dob": "1990-01-01" },
  "vehicle_registration":     { "plate": "กข 1234", "province": "กรุงเทพ" }
}
```

### `/data/sequence.json`  (thread-safe via `fcntl.flock`)

```json
{"CD": 13, "H": 2}
```

### `/data/token_records/YYYY-MM.jsonl`  (one JSON object per line)

```jsonl
{"timestamp":"2026-02-26T10:00:00Z","operation":"categorise","user_id":"Uxxx","input_tokens":420,"output_tokens":12,"cost_usd":0.000161}
```

---

## 6. API Endpoints

| Method | Path | Handler | Auth |
|---|---|---|---|
| GET | `/` | `root()` | none |
| GET | `/health` | `health_check()` | none |
| POST | `/callback` | `callback()` | LINE HMAC-SHA256 |
| POST | `/webhook` | `webhook()` (alias) | LINE HMAC-SHA256 |
| GET | `/reviewer` | `reviewer_dashboard()` | none (internal) |
| GET | `/reviewer/document` | `reviewer_get_document()` | none |
| POST | `/reviewer/useful` | `reviewer_mark_useful()` | none |
| POST | `/reviewer/status` | `reviewer_update_status()` | none |
| GET | `/manager` | `manager_dashboard()` | none |
| GET | `/manager/data` | `manager_data()` | none |
| GET | `/admin` | `admin_dashboard()` | none |
| POST | `/admin/loglevel` | `admin_set_loglevel()` | none |
| GET | `/admin/tokens` | `admin_token_usage()` | none |

> **Note:** Dashboard routes currently have no authentication. A future task is
> to add HTTP Basic Auth or JWT gating before production deployment.

---

## 7. Document Processing Pipeline

```
User sends image
       │
       ▼
 Download image bytes via LINE Data API (httpx)
       │
       ▼
 ai.ocr.extract_id_from_image()   ← if in verifying_policy state
       │                              → CID or plate for policy lookup
       ▼
 ai.categorise.categorise_document()   ← if in uploading_documents state
       │
       ├─ "unknown"  → reject, ask re-upload
       │
       ├─ "driving_license" + CD with counterpart
       │     → store in session["awaiting_ownership_for"]
       │     → ask ownership question (QuickReply)
       │
       └─ everything else
             ▼
       ai.extract.extract_fields(image_bytes, category)
             │
             ▼
       storage.document_store.save_document()  → /data/claims/<id>/<key>_<ts>.jpg
       storage.claim_store.add_document_to_claim()
       storage.claim_store.update_extracted_data()
             │
             ▼
       Show doc_received_flex + updated checklist
       If all required docs present → show submit_prompt_flex
```

---

## 8. Mock Data (mock_data.py)

Two policy databases — no real DB in v2.0, replace with actual API calls when ready.

**Car Damage (CD) policies:**
- `POL-2024-001234` — Somchai J., plate กข 1234, Class 1, active
- `POL-2024-005678` — Malinee P., plate ขค 5678, Class 2+, active
- `POL-2024-009999` — Expired policy (used in tests)

**Health (H) policies:** (added in v2.0)
- `H-POL-2024-000101` — Somchai J., IPD 500,000 / OPD 50,000 / 3,000/night
- `H-POL-2024-000202` — Malinee P., IPD 1,000,000 / OPD 100,000 / 5,000/night

Search functions: `search_policies_by_cid()`, `search_policies_by_plate()`,
`search_policies_by_name()`, `search_health_policies_by_cid()`.

---

## 9. Test Suite

All **338 tests pass, 0 skipped** as of 2026-02-26. Run time ≈ 1.5 s.

```
tests/
  conftest.py                  ← shared fixtures
  test_data.py                 ← shared webhook payloads & stubs
  test_api_endpoints.py        ← HTTP endpoint contracts
  test_business_logic.py       ← state machine, sequence, keyword detection, signatures
  test_conversation_flows.py   ← full flow via TestClient (CD + H paths)
  test_webhook_security.py     ← HMAC, malformed payloads, PII safety
  test_flex_messages.py        ← Flex Message builder contracts
  test_session_manager.py      ← session get/set/reset/isolation
```

**Run commands:**
```bash
# Full suite
.venv/bin/python -m pytest tests/ -v --tb=short

# Filtered gates (markers applied to all classes)
.venv/bin/python -m pytest -m unit          # pure logic only, no I/O, <0.5 s
.venv/bin/python -m pytest -m security      # signature + PII tests only
.venv/bin/python -m pytest -m integration   # full E2E via TestClient
.venv/bin/python -m pytest -m flow_cd       # Car Damage flows only
```

**Key `conftest.py` fixtures:**

| Fixture | What it patches | Scope |
|---|---|---|
| `mock_gemini` | `ai._model` (the shared `GenerativeModel` instance) | function |
| `mock_line_api` | `main.ApiClient`, `main.MessagingApi` | function |
| `mock_image_download` | `httpx.Client` | function |
| `mock_policy_lookup` | `handlers.identity.search_policies_by_*` | function |
| `set_session(uid, data)` | Directly writes `main.user_sessions[uid]` | function |
| `get_session(uid)` | Reads `main.user_sessions[uid]` | function |
| `clean_sessions` | Clears `user_sessions` before+after every test | autouse |
| `app_client` | `TestClient(app)` — exceptions propagate (reveals real bugs) | function |
| `lenient_client` | `TestClient(app, raise_server_exceptions=False)` — for malformed-payload / 4xx-5xx tests only | function |
| `tmp_data_dir` | Temp dir; patches `DATA_DIR` env var so storage resolves correctly | function |
| `_set_env_vars` | Sets fake `LINE_CHANNEL_*`, `GEMINI_API_KEY`, `DATA_DIR` | session |
| `_stub_genai` | Replaces `sys.modules["google.generativeai"]` with MagicMock | session |

---

## 10. Known Gaps & Recommended Next Tasks

These items are not yet implemented and should be prioritised by the next developer:

| Priority | Task | Notes |
|---|---|---|
| 🔴 High | **Dashboard authentication** | `/reviewer`, `/manager`, `/admin` are open. Add HTTP Basic Auth (quickest: FastAPI `HTTPBasic` dependency + `ADMIN_USER`/`ADMIN_PASSWORD` env vars) or LINE Login JWT before any deployment. |
| 🔴 High | **Replace mock_data with real policy API** | `handlers/identity.py` calls `mock_data.*`. Swap for actual insurer API (REST or DB). Define interface via Protocol class. |
| 🔴 High | **Thread-safe `user_sessions`** | Global `dict` is not safe under multi-worker uvicorn or concurrent async requests. Short-term: `asyncio.Lock`. Long-term: Redis session store. |
| 🟠 Medium | **Health claim counterpart flow** | Health claims skip `waiting_for_counterpart` but `handle_document_image` still checks `has_counterpart`. Verify H flow is complete end-to-end. No integration test yet for H OCR path. |
| 🟠 Medium | **GDPR / PII purge** | No mechanism to delete `/data/claims/{id}` or session data. Need a data retention policy + cleanup job. |
| 🟠 Medium | **Kubernetes manifests** | `docker-compose.yml` is ready but no K8s `Deployment.yaml`, `PersistentVolumeClaim.yaml`, `Secret.yaml` exist yet. |
| 🟡 Low | **AI prompt versioning** | Prompts are hardcoded in `ai/extract.py`, `ai/categorise.py`. Externalise to a YAML prompt registry for easier tuning. |
| 🟡 Low | **Token cost alerting** | Token JSONL is written but no alert fires when cost exceeds threshold. Add a daily aggregation job. |
| 🟡 Low | **Health claim OCR integration test** | `TestPolicyVerificationByImage` only covers CD. Add a test for H CID image → `search_health_policies_by_cid`. |
| 🟡 Low | **Type hints on handler functions** | Handler signatures use bare `Dict` without full generics. Add `dict[str, dict]` style hints and `-> None` returns throughout. |

---

## 11. Environment Variables Reference

See `.env.example` for full list. Critical vars:

| Variable | Required | Default | Notes |
|---|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | — | LINE developer console |
| `LINE_CHANNEL_SECRET` | ✅ | — | Used for HMAC-SHA256 webhook verification |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio |
| `DATA_DIR` | — | `/data` | Mount a PVC here in K8s |
| `LINE_API_HOST` | — | `https://api.line.me` | Override for mock-chat local testing |
| `LINE_DATA_API_HOST` | — | `https://api-data.line.me` | Override for mock-chat local testing |
| `LOG_LEVEL` | — | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PORT` | — | `8000` | Uvicorn bind port |
| `GEMINI_MODEL` | — | `models/gemini-2.5-flash` | Override to test other models |
| `REPO_URL` / `BRANCH` | — | — | If set, `entrypoint.sh` git-clones/pulls on start (GitOps pattern) |

---

## 12. Development Workflow

```bash
# 1. Install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Copy and fill env vars
cp .env.example .env
# edit .env

# 3. Run locally (no Docker)
.venv/bin/python main.py

# 4. Expose via ngrok (dev)
.venv/bin/python ngrok.py

# 5. Run with Docker Compose
docker-compose up --build

# 6. Run tests
.venv/bin/python -m pytest tests/ -v --tb=short

# 7. Run with mock-chat service (local LINE simulator)
docker-compose --profile dev up
```

---

## 13. Coding Conventions Established in This Codebase

1. **No `print()` statements** — always use `logger.info/debug/warning/error/exception`. `main.py` uses `logger = logging.getLogger(__name__)` at module level. Never log raw user message text (PII).
2. **Handlers are pure functions** — they receive `line_bot_api`, `event` (may be `None` in push contexts), `user_id`, `user_sessions`, and input data. No globals.
3. **Session access** — always use `session.get("key")` (not `session["key"]`) for optional fields to avoid `KeyError` in partially-seeded test sessions.
4. **`claim_id` guard** — every `claim_store.*` call is wrapped in `if claim_id:` because test sessions may not have a claim yet.
5. **Imports inside handlers** — handler functions import `flex_messages` and `storage` modules locally (inside the function) to avoid circular imports.
6. **12-Factor imports** — `constants.py` is the single source of truth; no magic strings in handlers.
7. **All monetary values** — stored as `float` (THB), never string.
8. **Filenames in storage** — format: `{category}_{YYYYMMDD}_{HHMMSS}.{ext}` generated by `document_store.save_document()`.
9. **Webhook error handling** — `_handle_webhook` catches `InvalidSignatureError` → 400, `ValueError/KeyError/UnicodeDecodeError` (malformed body) → 400. Do **not** catch `Exception` broadly in the webhook layer; let FastAPI's global handler emit 500 and log automatically.
10. **Test client split** — use `app_client` (exceptions propagate) for all normal tests; use `lenient_client` only when a test deliberately sends malformed/invalid payloads and needs to inspect the 4xx/5xx response.

---

## 14. Git History Summary

| Commit | Description |
|---|---|
| `eb66558` | Updated business requirement and user journey |
| `9583442` | Add spec from document-verify project |
| `b7a8a21` | Add current technical spec and business requirements |
| `0b54808` | Merge branch 'gcp' (last commit on `main`) |

All v2.0 code (constants, storage, ai, handlers, dashboards, tests, main.py rewrite)
and the 2026-02-26 code-quality fixes (import cleanup, print→logger, webhook 400 fix,
test assertion improvements, pytest markers) are in the **working tree** of branch
`add_doc_verify` and have **not yet been committed**. The next developer should:

```bash
git add -A
git commit -m "feat: implement v2.0 full claim pipeline + code quality fixes (CD+H, storage, AI, dashboards, tests)"
git push origin add_doc_verify
# Then open a PR: add_doc_verify → main
```

---

## 15. Handover Checklist for Next Developer

- [ ] Read `document/business-requirement.md` (BRD v2.0) — source of truth for features
- [ ] Read `document/tech-spec.md` — storage schema, API spec, state machine
- [ ] Confirm `338 tests pass` before making any changes
- [ ] Commit current working tree and push (see §14 above)
- [ ] Open PR from `add_doc_verify` → `main`
- [ ] Address "Known Gaps" in §10 in priority order:
  - [ ] Add dashboard authentication (`ADMIN_USER` / `ADMIN_PASSWORD` env vars + `HTTPBasic` dependency)
  - [ ] Replace `mock_data.py` lookups with real insurer policy API
  - [ ] Add `asyncio.Lock` around `user_sessions` writes (short-term thread safety)
  - [ ] Verify Health claim end-to-end flow and add H OCR integration test
- [ ] Create Kubernetes manifests (`k8s/` folder) for PVC, Deployment, Service, Secret
- [ ] Set up CI pipeline: `pytest` on PR, Docker build on merge to main

---

## 16. Session Log

| Date | Developer | Summary |
|---|---|---|
| 2026-02-26 | GitHub Copilot (Claude Sonnet 4.6) | Built v2.0 full pipeline (CD+H, storage, AI, dashboards, tests). 193 tests. |
| 2026-02-26 | Antigravity (Gemini) | Code quality review & fixes: duplicate imports removed, all `print()`→`logger.*`, webhook returns 400 for malformed body (was 500), `raise_server_exceptions=False` removed from test client, 3 vacuous assertions replaced, exact state assertions in flow tests, `@pytest.mark.unit/integration/security/flow_cd` applied to all 30+ test classes, `asyncio_mode = auto` added. **338 tests, all green.** |

---

*This document was last updated by Antigravity (Google Deepmind) on 2026-02-26.*
