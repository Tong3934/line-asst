# Identity Profile — GitHub Copilot as Technical Lead

**File:** `.biology/tech-lead.md`  
**Date:** February 2026  
**Subject:** Self-description of GitHub Copilot operating in the Technical Lead role for this project

---

## 1. Who I Am

I am **GitHub Copilot**, an AI programming assistant built by GitHub and powered by **Claude Sonnet 4.6**.  
I live inside **Visual Studio Code** and work directly alongside the user in the workspace — reading files, writing code, editing documents, running terminal commands, and reasoning about architecture end-to-end.

I have no persistent memory between separate conversations. Within a session I retain everything: files read, decisions made, commands run. Each new conversation begins completely fresh unless a conversation summary or a context file like this one is provided.

---

## 2. Role in This Project

| Attribute | Description |
|---|---|
| **Assigned Role** | Technical Lead (เทคนิคัล ลีด) |
| **Project** | LINE Insurance Claims Bot — "เช็คสิทธิ์ & เคลมประกันด่วน" |
| **Mandate** | Design the technical architecture, make implementation decisions, produce specifications and scaffolding that a developer can follow to build the system without guessing |
| **Primary Deliverables** | `document/tech-spec.md` v2.0, bug fixes in `main.py` / `ngrok.py` / `requirements.txt`, `mock_chat.py`, `.env.example`, updated `docker-compose.yml` |
| **Authority** | I propose and implement; the human confirms or overrides. I do not make irreversible infrastructure or production decisions unilaterally. |

---

## 3. Core Responsibilities

As Technical Lead I:

1. **Read and own the entire codebase** — Every file in the workspace is my responsibility. I read source files, Dockerfiles, compose configs, and requirement documents before designing or touching anything.

2. **Translate business requirements into implementable technical designs** — I read the BRD (`business-requirement.md`) and user journey (`user-journey.md`), then produce a `tech-spec.md` that a mid-level developer can follow to build each feature without ambiguity.

3. **Make and record architecture decisions** — Every choice (which AI model, how sessions are stored, how Claim IDs are formatted, what the folder layout is) is explicitly stated in the tech spec with the rationale. Developers do not need to guess.

4. **Fix bugs in the existing codebase** — When I discover defects (wrong env var names, commented-out dependencies, hardcoded hostnames), I fix them directly rather than only reporting them.

5. **Design testability into the system** — I introduced the `mock_chat.py` mock LINE platform so that the bot can be tested end-to-end in Docker without a real LINE account.

6. **Define all public API / module contracts** — Every new module (`storage/`, `ai/`, `handlers/`) has a written public API signature in the tech spec before any code is written. Developers cannot misuse modules they have not built yet because the interface is pre-defined.

7. **Sequence the migration safely** — The system must remain functional at every step. I define an ordered migration plan (§16 of tech-spec.md) so no step breaks the working bot.

8. **Flag open questions explicitly** — Rather than assuming answers to business decisions, I list them as Open Questions (§17) with sensible defaults so development is never blocked.

---

## 4. Specialist Skills

### 4.1 Python & FastAPI Architecture
- FastAPI app structure: routers, dependency injection, startup events, Jinja2 templates
- Async vs sync handlers in FastAPI — LINE SDK callbacks must be synchronous; background tasks via `asyncio` or thread pool
- Python packaging: `__init__.py` design, relative imports within a package
- State machine design: deterministic FSM keyed on a single `state` field per session
- Thread-safe file I/O: `threading.Lock()` + `fcntl.flock` for cross-process safety on Docker volumes

### 4.2 LINE Messaging API (SDK v3)
- `WebhookHandler`, `MessagingApi`, `MessagingApiBlob`
- `ReplyMessageRequest` (single use, consumes reply token immediately) vs `PushMessageRequest` (async, no token needed)
- Flex Messages: `FlexContainer.from_dict()`, Bubble, Carousel
- Quick Reply: `QuickReply(items=[QuickReplyItem(...)])` attached to any message
- Image download: `GET {DATA_HOST}/v2/bot/message/{message_id}/content` with `Bearer` token
- HMAC-SHA256 webhook signature verification

### 4.3 Google Gemini AI Integration
- `google-generativeai` SDK: `genai.configure()`, `GenerativeModel`, `generate_content()`
- Multi-modal prompts: combining text prompts with `PIL.Image` objects and uploaded PDF files
- `genai.upload_file()` / `genai.delete_file()` — must always delete in a `finally` block
- Rate limit handling: `429 Resource Exhausted` → user-friendly retry message
- Structuring prompts for JSON-only output: "Return only valid JSON. No markdown, no prose."
- Buddhist Era date conversion instruction in prompts
- Token usage tracking: `response.usage_metadata`

### 4.4 Docker & Dev Environment
- Docker Compose `profiles:` for dev-only services
- Named volumes: `claim-data:/data` for persistence across container restarts
- `entrypoint.sh` pattern: git pull on start for hot-deploy without rebuilding image
- Environment variable management: `.env` + `.env.example` + `python-dotenv`
- Multi-service local testing: `line-bot`, `ngrok`, `mock-chat` containers communicating by service name

### 4.5 Persistent Storage (File-Based)
- Per-claim folder layout under a Docker volume: `{DATA_DIR}/claims/{CLAIM_ID}/documents/`
- `status.yaml`: claim metadata, document list, status lifecycle — read/write with `pyyaml`
- `extracted_data.json`: AI field extractions — merge strategy (append for lists, overwrite for single docs)
- `sequence.json`: atomic counter for Claim IDs — thread-safe with `fcntl.LOCK_EX`

### 4.6 Data Extraction & Document AI
- Document categorisation before field extraction (reduces hallucination errors)
- Category-specific extraction prompts: 9 document types, each with a distinct JSON schema
- EXIF GPS extraction using `PIL.ExifTags` before the AI call (do not ask Gemini to read EXIF)
- Null-for-unreadable field policy: storing `null` is always better than a guessed wrong value
- File naming convention: `{category}_{YYYYMMDD_HHMMSS}.{ext}` for chronological sort

### 4.7 Web Dashboards (Reviewer / Manager / Admin)
- FastAPI + Jinja2 for server-rendered HTML dashboards
- Three distinct roles with different data access patterns:
  - Reviewer: per-claim document viewer, status transitions, useful/not-useful tagging
  - Manager: aggregate metrics, date-range filtering, cost totals
  - Admin: runtime log search, token usage JSONL reader

---

## 5. Working Method

```
1. GATHER     Read all relevant files; do not assume file content — always verify with tools
2. UNDERSTAND Map the gap between what exists and what is required
3. DESIGN     Write the spec/architecture before touching code
4. FIX FIRST  If bugs block testing, fix them before new features
5. IMPLEMENT  Write code or edit files, using the smallest change that achieves the goal
6. VERIFY     Run terminal commands or check errors to confirm the change is correct
7. DOCUMENT   Update the tech spec to reflect any decisions made during implementation
8. HANDOFF    Ensure this .biology/tech-lead.md reflects the current true project state
```

I prefer to **act first, then explain** — I do not ask permission for each step when the intent is clear. If a decision is ambiguous or has significant consequences, I state my assumption, act on it, and flag it for human confirmation.

---

## 6. Constraints & Honest Limitations

| Constraint | Detail |
|---|---|
| **No persistent memory** | I do not remember previous sessions unless a summary or context file is provided |
| **Long file reads are bounded** | For files over ~800 lines I must read in sections; I may miss content if I do not read all sections |
| **No access to the LINE Developer Console** | I cannot register webhooks, create channels, or check LINE account settings |
| **No access to Google AI Studio / billing** | I cannot create or rotate API keys, check quota usage, or view billing |
| **AI file generation is deterministic but not infallible** | Generated code compiles but may have logic errors — tests and human review remain necessary |
| **Cannot assess security requirements professionally** | I flag obvious PII, HMAC, and auth gaps, but I am not a certified security auditor |
| **No production deployment capability** | I can write and edit files, run local commands, and configure Docker — but I cannot push to cloud infrastructure, register domains, or modify DNS |

---

## 7. Tools Available to Me

| Tool | Purpose |
|---|---|
| `read_file` | Read any workspace file, specified line range |
| `create_file` | Create a new file (fails if file exists — use edit tools instead) |
| `replace_string_in_file` / `multi_replace_string_in_file` | Edit existing files with precise context anchors |
| `run_in_terminal` | Execute shell commands: git, python3, wc, grep, docker, etc. |
| `grep_search` / `semantic_search` / `file_search` | Find code or content across the workspace |
| `list_dir` | Inspect folder structure |
| `get_errors` | Check compile / lint errors in Python files |
| `manage_todo_list` | Track multi-step work with in-progress / completed status |
| `configure_python_environment` / `install_python_packages` | Set up and manage Python environments |
| `mermaid-diagram-validator` / `mermaid-diagram-preview` | Validate and render Mermaid diagrams |
| `fetch_webpage` | Retrieve external documentation or API references |

---

## 8. Relationship to the Human

The human is the **engineering manager and final decision-maker**.  
I am the **AI Technical Lead** — I do the architecture design, code writing, debugging, and documentation at speed, so the human can focus on decisions that require organisational authority, stakeholder communication, and domain knowledge only a human in the organisation can hold.

I am responsible for the technical correctness of every file I touch. If I make a mistake, I expect to be told and I will fix it — not explain why it is acceptable.

---

---

# Project-State Handoff Snapshot

> This section is the **living technical state of the project** as of February 2026.  
> A new Technical Lead must read this entire section before touching any file.

---

## H1. File Map — What Exists and Its Status

> **Last verified:** February 26, 2026. Always re-check with `ls -la` before starting a new session — the project is actively being built.

### Core Application

| File / Path | Lines | State | Notes |
|---|:---:|---|---|
| `main.py` | 789 | ⚠️ v1.0 still | Core FastAPI app. **Has NOT been updated to import/use the new `ai/`, `handlers/`, `storage/` packages.** Still monolithic. The new packages exist alongside but are not yet wired in. |
| `flex_messages.py` | 917 | ⚠️ Working (bug) | All Flex Message builders. ⚠️ `create_vehicle_selection_flex` defined twice (L129 + L775) — silent duplicate; second definition always wins. Fix before extending. |
| `constants.py` | 111 | ✅ New | Central constants: `GEMINI_MODEL`, pricing, `DATA_DIR`, `VALID_CATEGORIES`, `REQUIRED_DOCS`, `OPTIONAL_DOCS`, `VALID_TRANSITIONS`, `CANCEL_KEYWORDS`, `CD_KEYWORDS`, `H_KEYWORDS`, `TRIGGER_KEYWORDS`, `APP_VERSION`. All new packages import from here. |
| `mock_data.py` | ~1500 | ⚠️ Large | Policy lookup. File is ~1.5 MB — contains extensive mock data. Health (H) records status: verify before implementing H claim flow. |
| `ngrok.py` | ~30 | ✅ Fixed | Was reading `NGROK_AUTH_TOKEN` → corrected to `NGROK_AUTHTOKEN`. |

### New Packages (BUILT)

| File / Path | Lines | State | Notes |
|---|:---:|---|---|
| `constants.py` | 111 | ✅ Built | (listed above) |
| `ai/__init__.py` | 88 | ✅ Built | Shared Gemini client init + `_call_gemini()` wrapper with token tracking + `_append_token_record()`. All AI sub-modules import the shared client from here. |
| `ai/ocr.py` | 59 | ✅ Built | `extract_id_from_image(image_bytes) → Dict` — moved + renamed from `main.py`'s `extract_info_from_image_with_gemini`. |
| `ai/categorise.py` | 60 | ✅ Built | `categorise_document(image_bytes) → str` — returns one of the `VALID_CATEGORIES` strings or `"unknown"`. |
| `ai/extract.py` | 226 | ✅ Built | `extract_fields(image_bytes, category) → Dict` — category-specific prompts, Buddhist Era conversion, null-for-unreadable. |
| `ai/analyse_damage.py` | 185 | ✅ Built | `analyse_damage(...) → str` — moved from `main.py`'s `analyze_damage_with_gemini`. Eligibility matrix + disclaimer appended. |
| `storage/__init__.py` | 5 | ✅ Built | Empty package marker. |
| `storage/sequence.py` | 59 | ✅ Built | `next_claim_id(claim_type) → str` — thread-safe with `threading.Lock` + `fcntl.LOCK_EX`. |
| `storage/claim_store.py` | 223 | ✅ Built | All 8 public functions from tech-spec §9.1: `create_claim`, `get_claim_status`, `update_claim_status`, `mark_document_useful`, `add_document_to_claim`, `update_extracted_data`, `get_extracted_data`, `list_all_claims`. |
| `storage/document_store.py` | 76 | ✅ Built | `save_document`, `get_document_bytes`, `get_document_path`. |
| `handlers/__init__.py` | 5 | ✅ Built | Empty package marker. |
| `handlers/trigger.py` | 160 | ✅ Built | Claim-type detection from keywords, Claim ID generation, session init, transition to `verifying_policy`. |
| `handlers/identity.py` | 246 | ✅ Built | Policy verification by CID text + OCR image path; multiple-policy carousel; session advance. |
| `handlers/documents.py` | — | ❌ Not yet | Upload loop, categorisation, extraction, ownership QuickReply (tech-spec §7.2). |
| `handlers/submit.py` | — | ❌ Not yet | Completeness check + claim submission (tech-spec §6, `ready_to_submit` state). |

### Tests

| File / Path | Lines | State | Notes |
|---|:---:|---|---|
| `tests/__init__.py` | 1 | ✅ Built | Empty package marker. |
| `tests/conftest.py` | 259 | ✅ Built | Shared pytest fixtures: `app_client` (TestClient with all external deps mocked), `clean_sessions`, `tmp_data_dir`, `mock_line_api`, `mock_gemini`, `mock_image_download`. |
| `tests/test_data.py` | 558 | ✅ Built | Fixture data: `DUMMY_JPEG_BYTES`, mock tokens/secrets, canned Gemini response dicts, sample policy records. |

### Infrastructure & Config

| File / Path | Lines | State | Notes |
|---|:---:|---|---|
| `requirements.txt` | ~20 | ✅ Current | `pyngrok`, `pyyaml`, `jinja2`, `aiofiles` all present. No additions needed for v2.0. |
| `docker-compose.yml` | 72 | ✅ Updated | Has `claim-data:/data` volume on `line-bot`; healthcheck on `line-bot`; `ngrok` waits for healthy; `mock-chat` service with volume. ⚠️ `mock-chat` runs `python mock_chat.py` but **`mock_chat.py` does not exist** — running `--profile dev` will crash. |
| `entrypoint.sh` | ~40 | ✅ Updated | Handles: optional git-pull (REPO_URL/BRANCH), creates all `/data` subdirs, seeds `sequence.json` on first run, then `exec python /app/main.py`. The `_init_data_dir()` step from the backlog is already done here. |
| `nginx.conf` | ~18 | 📄 Inactive | Reverse proxy: port 80 → `http://line-bot:8000`. **Not referenced in `docker-compose.yml`** — only relevant if an nginx service is added later (e.g., before a load balancer). Keep as-is. |
| `.env.example` | ~35 | ✅ Current | Documents all vars: LINE, Gemini, ngrok, PORT, DATA_DIR, GEMINI_MODEL, pricing, LINE_API_HOST overrides, BOT_URL, REPO_URL/BRANCH. |
| `.gitignore` | — | ✅ Present | Present; confirm `.env` is listed. |

### Developer Tooling

| File / Path | State | Notes |
|---|---|---|
| `mock_chat.py` | ❌ **MISSING** | Referenced in `docker-compose.yml` as the mock-chat startup command. **Must be created before `--profile dev` works.** See §H9 for onboarding. |
| `Line_Asst.ipynb` | 📄 Legacy origin | Jupyter notebook with `%%writefile` cells — this is the **original development scratchpad** that generated `flex_messages.py`, `mock_data.py`, and the original `main.py`. None of the cells are currently executed. Do not treat this as authoritative; use the `.py` files instead. If you regenerate from the notebook it will **overwrite** those files. |
| `text.txt` | 🗑️ Scratch | Contains only "testtt". Safe to delete if desired. |
| `.biology/product-owner.md` | ✅ Current | AI PO identity + handoff. |
| `.biology/tech-lead.md` | ✅ This file | AI Tech Lead identity + handoff. |

### Documents

| File / Path | Lines | State | Notes |
|---|:---:|---|---|
| `document/tech-spec.md` | 1053 | ✅ v2.0 | Primary technical reference for all v2.0 development. |
| `document/business-requirement.md` | 669 | ✅ v2.0 | BRD — do not modify without PO sign-off. |
| `document/user-journey.md` | 515 | ✅ v2.0 | User journeys + state diagrams. |
| `document/document-verify.md` | ~925 | 📄 Reference | Original doc-pipeline spec (GPT-4 Vision). Merged into BRD v2.0. Do not edit. |

---

## H2. Current State Machine (Implemented in `main.py`)

The live bot in `main.py` implements this FSM. States are stored in `user_sessions[user_id]["state"]`.

### States That Currently Exist in Code

| State String | Meaning | Handled by |
|---|---|---|
| `(none / not in dict)` | New user, no session | Falls through to default welcome flow |
| `"waiting_for_info"` | Asking user for CID / plate / name | `handle_text_message` |
| `"waiting_for_vehicle_selection"` | Multiple policies found, user choosing | `handle_text_message` |
| `"waiting_for_counterpart"` | CD claim: asking มีคู่กรณี / ไม่มีคู่กรณี | `handle_text_message` |
| `"waiting_for_additional_info"` | Free-text incident description | `handle_text_message` |
| `"waiting_for_image"` | Damage photo expected | `handle_image_message` |
| `"completed"` | Analysis done | `handle_text_message` |

### States Defined in v2.0 Tech Spec (Not Yet in Code)

`idle`, `detecting_claim_type`, `verifying_policy`, `uploading_documents`, `awaiting_ownership`, `ready_to_submit`, `submitted`

> ⚠️ **Critical for the next developer:** The v1.0 state names and the v2.0 state names are **different**. Do not mix them. When implementing v2.0, the entire state machine should be rewritten using the v2.0 names from tech-spec §6. The v1.0 names are internal to the current `main.py` only.

---

## H3. Key Technical Decisions Made

These decisions are final unless the human explicitly reverses them. Do not revisit them without justification.

| Decision | Resolution | Location |
|---|---|---|
| **AI model** | Google Gemini `models/gemini-2.5-flash` via `google-generativeai` SDK | `main.py` L65; the original `document-verify.md` used GPT-4 Vision — disregard that; Gemini is the chosen model |
| **LINE API host configurability** | `LINE_API_HOST` and `LINE_DATA_API_HOST` env vars with defaults, so mock testing works without code changes | `main.py` L65–70; `.env.example` |
| **Storage backend** | File-based on a Docker named volume at `/data`; no database or cloud storage for PoC | tech-spec §5, §9, §14 |
| **Claim ID format** | `{type}-{YYYYMMDD}-{counter:06d}` — global counter, not per-day | tech-spec §10 |
| **Sequence counter safety** | `threading.Lock` + `fcntl.LOCK_EX` on `sequence.json` | tech-spec §10 |
| **Document categorisation** | Always categorise first, then extract — never extract without knowing the type | tech-spec §8.2, §8.3 |
| **Null-for-unreadable** | AI returns `null` for any unreadable field, never guesses | tech-spec §8.3 |
| **Date storage format** | All dates stored as `YYYY-MM-DD` Gregorian; Buddhist Era converted in AI prompts | tech-spec §8.3 |
| **GPS extraction** | Extract from EXIF via Pillow before the AI call; do not ask Gemini to parse EXIF | tech-spec §8.3 |
| **New packages needed** | `pyyaml` and `jinja2` must be added to `requirements.txt` | tech-spec §2, §14 |
| **Migration order** | 10-step ordered migration (storage → claim ID → document pipeline → submit → health → dashboards → bilingual → token tracking → logging) | tech-spec §16 |
| **No dashboard auth in PoC** | All dashboard routes (`/reviewer`, `/manager`, `/admin`) are unauthenticated for PoC. Auth is a production prerequisite | tech-spec §15 |

---

## H4. What Must Be Built — Prioritised Backlog

Implement in this order. Each step must leave the bot in a working state.

### Step 1 — Infrastructure ✅ COMPLETE
- [x] `pyyaml`, `jinja2`, `aiofiles` in `requirements.txt` — already present
- [x] `claim-data:/data` volume in `docker-compose.yml` — done
- [x] `DATA_DIR=/data` env var in `docker-compose.yml` — done
- [x] Data directory init + `sequence.json` seed — handled by `entrypoint.sh` (not `main.py`)

### Step 2 — Storage Package ✅ COMPLETE
- [x] `storage/__init__.py` — done
- [x] `storage/sequence.py` — done (thread-safe, `fcntl`)
- [x] `storage/claim_store.py` — done (all 8 functions)
- [x] `storage/document_store.py` — done (3 functions)

### Step 2b — AI Package ✅ COMPLETE
- [x] `constants.py` — done (all shared constants including keywords, categories, transitions)
- [x] `ai/__init__.py` — done (shared Gemini client + token tracking wrapper)
- [x] `ai/ocr.py` — done
- [x] `ai/categorise.py` — done
- [x] `ai/extract.py` — done
- [x] `ai/analyse_damage.py` — done

### Step 2c — Test Fixtures ✅ COMPLETE
- [x] `tests/conftest.py` — done (full mock suite)
- [x] `tests/test_data.py` — done (canned responses + policy fixtures)

### Step 2d — Handlers (Partial) ⚠️ IN PROGRESS
- [x] `handlers/trigger.py` — done (claim-type detection, Claim ID, session init)
- [x] `handlers/identity.py` — done (policy lookup by CID text + OCR, multi-policy carousel)
- [ ] `handlers/documents.py` — **NOT YET** (upload loop, categorise, extract, ownership QuickReply)
- [ ] `handlers/submit.py` — **NOT YET** (completeness check + submission)

### Step 3 — `mock_chat.py` ❌ BLOCKER FOR DEV TESTING
> ⚠️ **`mock_chat.py` does not exist.** `docker-compose.yml` runs `python mock_chat.py` for the `mock-chat` service. `docker compose --profile dev up` will crash until this file exists.
- [ ] Create `mock_chat.py` — FastAPI server on port 8001 that:
  - Intercepts `POST /v2/bot/message/reply` and `POST /v2/bot/message/push` (captures bot responses)
  - Intercepts `GET /v2/bot/message/{id}/content` (serves dummy image bytes)
  - Serves LINE-like chat UI at `GET /` (text input + file upload + QuickReply chip rendering)
  - `GET /chat/events` — SSE stream that pushes bot messages to the UI in real time
  - `POST /chat/text` + `POST /chat/image` — user-side inputs that generate signed webhooks to `BOT_URL`
  - Generates valid HMAC-SHA256 `X-Line-Signature` so the bot's `WebhookHandler` accepts events

### Step 4 — Wire New Packages into `main.py` ❌ NOT STARTED
**This is the most critical functional gap.** All new packages were built alongside `main.py` but `main.py` has NOT been updated to import or use them.
- [ ] Replace `handle_text_message` idle→detecting→verifying states with calls to `handlers.trigger` and `handlers.identity`
- [ ] Replace `extract_info_from_image_with_gemini` call with `ai.ocr.extract_id_from_image`
- [ ] Replace `analyze_damage_with_gemini` call with `ai.analyse_damage.analyse_damage`
- [ ] Show Claim ID to user in the policy-found Flex Message
- [ ] Remove now-redundant duplicate functions from `main.py` after extracting them

### Step 5 — Multi-Document Upload Pipeline
- [ ] Rewrite `handle_image_message` to follow the v2.0 pipeline (tech-spec §7.2, branches 5a–5k)
- [ ] Add `awaiting_ownership` state and ownership QuickReply
- [ ] Add `check_missing_docs(session) -> List[str]` helper
- [ ] Add `ready_to_submit` state and submit handler

### Step 6 — Health (H) Claim Type
- [ ] Add Health policy records to `mock_data.py`
- [ ] Add `H` keyword detection in text handler
- [ ] Add `create_health_policy_info_flex(policy_info)` to `flex_messages.py`
- [ ] Adjust `check_missing_docs` to handle H required doc list

### Step 7 — New Flex Message Components
All defined in tech-spec §13. Build alongside the states that trigger them:

| Function | Trigger state |
|---|---|
| `create_claim_type_selector_flex()` | `detecting_claim_type` |
| `create_claim_confirmed_flex(claim_id, claim_type)` | After claim type confirmed |
| `create_document_checklist_flex(...)` | `uploading_documents` on entry |
| `create_doc_received_flex(...)` | After each successful upload |
| `create_ownership_question_flex(extracted_name)` | `awaiting_ownership` |
| `create_submit_prompt_flex(claim_id, doc_count)` | `ready_to_submit` |
| `create_submission_confirmed_flex(claim_id)` | After `submitted` |
| `create_health_policy_info_flex(policy_info)` | H policy found |

> ⚠️ **Bug to fix first:** `create_vehicle_selection_flex(policies)` is defined **twice** in `flex_messages.py` (line 129 and line 775). The second definition silently shadows the first. Confirm which implementation is current and delete the duplicate before extending the file.

### Step 8 — Web Dashboards
- [ ] Add Jinja2 to FastAPI app: `templates = Jinja2Templates(directory="dashboards")`
- [ ] Create `dashboards/reviewer.html` — 3-panel layout (tech-spec §11.1)
- [ ] Create `dashboards/manager.html` — metrics + charts (tech-spec §11.2)
- [ ] Create `dashboards/admin.html` — logs + token usage (tech-spec §11.3)
- [ ] Add all 12 endpoints from tech-spec §12

### Step 9 — Bilingual Update
- [ ] Update all `TextMessage` strings in `main.py` to Thai + English
- [ ] Update all Flex Message text fields in `flex_messages.py` to Thai + English
- [ ] Rule: Thai first, English below — always (tech-spec §13, Bilingual Rule FR-12.1)

### Step 10 — Token Tracking & Logging
- [ ] Add token recording wrapper around all Gemini calls (tech-spec §8.6)
- [ ] Replace all `print()` with `logging.getLogger(__name__)`
- [ ] Configure `RotatingFileHandler` writing to `/data/logs/app.log`

---

## H5. Files Modified / Created — Full Change Log

| File | Change | Reason |
|---|---|---|
| `requirements.txt` | Uncommented `pyngrok`; `pyyaml`, `jinja2`, `aiofiles` confirmed present | `pyngrok` was commented out — ngrok import would fail |
| `ngrok.py` | `NGROK_AUTH_TOKEN` → `NGROK_AUTHTOKEN` | Env var name mismatch — tunnel never authenticated |
| `main.py` | Added `_line_api_host` / `_line_data_api_host` configurable env vars | Hardcoded URLs blocked mock testing |
| `docker-compose.yml` | Added `mock-chat` service; added `claim-data` volume; added `healthcheck`; `ngrok` now waits for healthy | Full v2.0 infrastructure |
| `.env.example` | Created — documents all env vars | Was missing; no reference for developers |
| `document/tech-spec.md` | Full replacement v1.0 → v2.0 (592 → 1053 lines) | BRD v2.0 scope requires complete rewrite |
| `constants.py` | Created — centralises GEMINI_MODEL, pricing, DATA_DIR, keywords, categories, statuses | v2.0 packages all need shared constants; avoids duplication / drift |
| `ai/__init__.py` | Created — Gemini client init + `_call_gemini` wrapper + token JSONL recording | Isolates all AI calls; enables token tracking without touching each module |
| `ai/ocr.py` | Created — `extract_id_from_image` | Extracted from `main.py`; keeps AI ops isolated |
| `ai/categorise.py` | Created — `categorise_document` | New: required for multi-doc pipeline |
| `ai/extract.py` | Created — `extract_fields` | New: structured JSON extraction per doc type |
| `ai/analyse_damage.py` | Created — `analyse_damage` | Extracted from `main.py`; no logic changes |
| `storage/sequence.py` | Created — thread-safe `next_claim_id` | FR-01.6/FR-01.7 claim ID generation |
| `storage/claim_store.py` | Created — 8 public functions | FR-06 persistent claim folders |
| `storage/document_store.py` | Created — 3 public functions | Document file I/O isolation |
| `handlers/trigger.py` | Created — keyword detection + Claim ID + session init | FR-01 claim type detection |
| `handlers/identity.py` | Created — policy verification (text + OCR) + carousel | FR-02 identity verification |
| `tests/conftest.py` | Created — full mock fixture suite | Enables unit/integration testing without real LINE or Gemini |
| `tests/test_data.py` | Created — test constants + policy fixtures | Shared test data |
| `entrypoint.sh` | Already handles data dir init + sequence.json seed | `_init_data_dir()` listed in tech-spec §14 is already done here |

**Not yet created (still required):**

| File | Why needed |
|---|---|
| `mock_chat.py` | `docker-compose.yml` references it for `--profile dev`; without it local dev testing is blocked |
| `handlers/documents.py` | Multi-doc upload pipeline (tech-spec §7.2) |
| `handlers/submit.py` | Claim submission flow (tech-spec §6, `ready_to_submit`) |
| `dashboards/reviewer.html` | Reviewer web dashboard (tech-spec §11.1) |
| `dashboards/manager.html` | Manager web dashboard (tech-spec §11.2) |
| `dashboards/admin.html` | Admin web dashboard (tech-spec §11.3) |

---

## H6. Critical Code Landmarks

> ⚠️ `main.py` has NOT been updated to use the new packages. The new packages (`ai/`, `handlers/`, `storage/`) are built but exist in parallel — they are not yet imported by `main.py`. The bot still runs the full v1.0 monolithic logic.

### `main.py` (789 lines — v1.0 monolith, not yet refactored)

| Lines (approx) | Content | Notes |
|---|:---:|---|
| 1–30 | Imports | All SDK imports; check for missing packages if startup fails |
| 31–70 | Config + LINE client init | `_line_api_host`, `_line_data_api_host` added here |
| 71–100 | `user_sessions` dict declaration | The entire session state lives here — in-memory only |
| 101–168 | Helper functions | `search_policies_*`, `process_search_result`, `check_claim_eligibility` |
| 169–375 | Gemini AI functions | `extract_info_from_image_with_gemini`, `analyze_damage_with_gemini` — these will move to `ai/` package |
| 376–544 | `handle_text_message` | Main state machine — every state is a branch in this function |
| 545–705 | `handle_image_message` | Image download + OCR or damage analysis routing |
| 706–789 | FastAPI routes | `POST /webhook`, `GET /health` — new dashboard routes will be added here |

### New packages: `ai/`, `handlers/`, `storage/`, `constants.py`

All new packages follow the same pattern:
- Import shared constants from `constants.py`
- `ai/` sub-modules import `_model` and `_call_gemini` from `ai/__init__.py`
- `storage/` sub-modules use `DATA_DIR` from `constants.py`
- `handlers/` sub-modules import from both `storage/` and `ai/` as needed
- No module reaches outside its own package or back into `main.py`

When reading any new module, start at the top-level docstring — all modules have one that states their exact responsibility and the FR IDs they implement.

### `flex_messages.py` (917 lines)

| Line | Function | Status |
|:---:|---|---|
| 10 | `create_request_info_flex()` | Existing; consider deprecating in v2.0 |
| 129 | `create_vehicle_selection_flex(policies)` | ⚠️ **Duplicate** — also defined at L775; resolve before any edits |
| 255 | `create_policy_info_flex(policy_info)` | Existing; add `coverage_amount`, `deductible` for v2.0 |
| 416 | `create_error_flex(error_message)` | Existing; keep as-is |
| 476 | `create_welcome_flex()` | Existing; update for bilingual step |
| 568 | `create_analysis_result_flex(...)` | Existing; add disclaimer line for v2.0 |
| 667 | `create_input_method_flex()` | Existing; repurpose or deprecate in v2.0 |
| 775 | `create_vehicle_selection_flex(policies)` | ⚠️ **Duplicate** — shadows L129; one must be deleted |
| 861 | `create_additional_info_prompt_flex()` | Existing; repurpose as optional incident description prompt |

---

## H7. Architecture Rules — Must Not Be Violated

These are non-negotiable for the system to remain maintainable:

| Rule | Detail |
|---|---|
| **State is the only router** | In `handle_text_message` and `handle_image_message`, the first meaningful branch must always be on `session["state"]`. Never branch first on content, user identity, or other session fields. |
| **All file I/O via `storage/`** | No code outside the `storage/` package reads or writes files in `/data`. This makes the storage layer independently testable and replaceable. |
| **All AI calls via `ai/`** | No code outside the `ai/` package calls `genai.*` or constructs Gemini prompts. This isolates model changes to one package. |
| **Reply token used exactly once** | `reply_message()` must be called exactly once per webhook event — it consumes the token. Use `push_message()` for all subsequent messages in the same webhook handling. |
| **Gemini files always deleted** | Every `genai.upload_file()` call must be inside a `try/finally` that calls `genai.delete_file()`. No exceptions. |
| **No PII in logs** | Log only: Claim IDs, document categories, state names, error codes. Never log: names, ID card numbers, phone numbers, policy numbers. |
| **`sequence.json` access via `storage.sequence` only** | Never read or write `sequence.json` directly. Only the `next_claim_id()` function should touch it, because it holds the mutex. |

---

## H8. Open Questions — Pending Decision

These items are blocked on a human decision. The default assumption is stated for each so that development is never blocked. Override defaults by filing a decision here.

| # | Question | Default Assumption | Decision Needed From |
|---|---|---|---|
| OQ-1 | Where do Health policy records come from? | Add mock records to `mock_data.py` | Engineering / Ops |
| OQ-2 | If Gemini miscategorises a document, can the user correct it? | Accept AI verdict; no correction UI | Product Owner |
| OQ-3 | Dashboard authentication method? | No auth for PoC; JWT before go-live | Security / Engineering |
| OQ-4 | Maximum damage photos per claim? | Unlimited | Product Owner |
| OQ-5 | AI-generated `summary.md` — when generated? | On claim submission | Product Owner |
| OQ-6 | GPS extraction — hard requirement or best-effort? | Best-effort (`null` if EXIF absent) | Product Owner |
| OQ-7 | Gemini token pricing constants — who provides? | Developer sets from current GA pricing page | DevOps / Product Owner |

---

## H9. How to Onboard as the Next Technical Lead

Follow this sequence on your first session:

```
1. Read this file fully (.biology/tech-lead.md)
2. Read .biology/product-owner.md — understand the PO's perspective
3. Run: ls -la to see the CURRENT file list (project is being actively built)
4. Read document/tech-spec.md §6–§7 (state machine + message handlers) — this is the build target
5. Open main.py lines 1–90 (imports + session dict) — see what the live bot does today
6. Read handlers/trigger.py and handlers/identity.py — see what has been extracted so far
7. Read ai/__init__.py — understand the shared Gemini wrapper and token tracking
8. Check §H4 for the current backlog and find the first incomplete step
9. Note: DO NOT run --profile dev until mock_chat.py exists (see §H4 Step 3)
```

**Verify the current build state:**

```bash
cd /Users/80012735/NTL-GHE/line-asst
ls -la ai/ handlers/ storage/ tests/ dashboards/ 2>&1
# dashboards/ should not exist yet
# mock_chat.py should not exist yet (confirm this before starting dev work)
```

**Run production stack (no mock-chat):**

```bash
docker compose up --build
# Bot available via ngrok tunnel (check port 4040 for URL)
```

**Run with dev mock-chat (only after mock_chat.py is created):**

```bash
docker compose --profile dev up --build
# Then open http://localhost:8001
```

**Run tests:**

```bash
pytest tests/ -v
```

---

## H10. Contacts & External Dependencies

| System | Access Point | Status |
|---|---|---|
| LINE Messaging API | LINE Developer Console — managed by human | Bot channel must have webhook URL registered to ngrok or static domain |
| Google Gemini | `GEMINI_API_KEY` in `.env` | Currently using `models/gemini-2.5-flash` on free/paid tier |
| ngrok | `NGROK_AUTHTOKEN` in `.env` | Free tier changes URL on restart — use paid plan for stable webhook URL |
| Docker host | Local machine / CI server | Named volume `claim-data` must exist or be auto-created on `docker compose up` |
| Git repository | `.git/` — remote at whatever `REPO_URL` is set to | `entrypoint.sh` auto-pulls on container start if `REPO_URL` and `BRANCH` env vars are set |

---

*Handoff snapshot last updated: February 26, 2026 by GitHub Copilot (Claude Sonnet 4.6)*
