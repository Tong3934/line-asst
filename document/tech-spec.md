# Technical Specification — LINE Insurance Claim Bot

**Project Name:** LINE Insurance Claim Bot (เช็คสิทธิ์เคลมด่วน)  
**Version:** 1.0.0  
**Last Updated:** February 2026  
**Maintainer:** Technical Development Team

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [Environment Variables](#5-environment-variables)
6. [API Endpoints](#6-api-endpoints)
7. [User Conversation Flow (State Machine)](#7-user-conversation-flow-state-machine)
8. [Core Modules](#8-core-modules)
9. [Data Model](#9-data-model)
10. [AI Integration (Google Gemini)](#10-ai-integration-google-gemini)
11. [LINE Flex Message UI Components](#11-line-flex-message-ui-components)
12. [Deployment](#12-deployment)
13. [Known Limitations & Future Work](#13-known-limitations--future-work)

---

## 1. Project Overview

This system is a **LINE Messaging API chatbot** that helps insurance policyholders quickly check their vehicle insurance claim eligibility ("เช็คสิทธิ์เคลมด่วน"). Users interact via LINE Chat. The bot guides them through a structured multi-step conversation to:

1. Identify the policyholder and their insured vehicle.
2. Capture contextual information (counterpart presence, incident description).
3. Receive an AI-powered damage analysis and claim eligibility verdict based on their policy document.

The bot is powered by **Google Gemini AI** for both OCR (reading ID cards / license plates from images) and multi-modal damage analysis (comparing a damage photo against the actual policy PDF).

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      LINE Platform                          │
│   User ──► LINE App ──► LINE Messaging API ──► Webhook      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS POST /webhook
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Docker Host (docker-compose)                │
│                                                             │
│  ┌─────────────────────────┐   ┌──────────────────────────┐ │
│  │     line-bot service    │◄──│      ngrok service       │ │
│  │  FastAPI (port 8000)    │   │  ngrok/ngrok:latest      │ │
│  │  Python 3.11-slim       │   │  Exposes :8000 publicly  │ │
│  │                         │   │  Dashboard: :4040        │ │
│  └──────────┬──────────────┘   └──────────────────────────┘ │
│             │                                               │
└─────────────┼───────────────────────────────────────────────┘
              │ HTTPS
              ▼
┌─────────────────────────────────────────────────────────────┐
│              External APIs                                  │
│  • Google Gemini AI  (generativelanguage.googleapis.com)    │
│  • LINE Data API     (api-data.line.me)                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Choice | Reason |
|---|---|---|
| Web Framework | FastAPI | Async support, automatic OpenAPI docs, lightweight |
| AI Provider | Google Gemini 2.5 Flash | Multi-modal (text + image + PDF), fast response |
| LINE SDK | `line-bot-sdk` v3 | Official SDK for LINE Messaging API |
| Tunneling | ngrok (Docker service) | No fixed public IP required for webhook |
| Session Storage | In-memory dict (`user_sessions`) | Simplicity; no persistence requirement for PoC |
| Image Transfer | httpx download + in-memory bytes | No local disk dependency for images |

---

## 3. Technology Stack

| Layer | Technology | Version / Notes |
|---|---|---|
| Language | Python | 3.11 |
| Web Framework | FastAPI | Latest |
| ASGI Server | Uvicorn | `uvicorn[standard]` |
| LINE Bot SDK | `line-bot-sdk` | v3 |
| AI Model | Google Gemini | `models/gemini-2.5-flash` |
| Image Processing | Pillow | Latest |
| HTTP Client | httpx | Latest |
| Config Management | python-dotenv | Latest |
| Containerisation | Docker + Docker Compose | `python:3.11-slim` base |
| Tunneling | ngrok | `ngrok/ngrok:latest` Docker image |

---

## 4. Repository Structure

```
line-asst/
├── main.py               # Application entry point; FastAPI app, webhook handler, all bot logic
├── flex_messages.py      # LINE Flex Message JSON templates (UI components)
├── mock_data.py          # Mock policy database + search functions
├── ngrok.py              # Standalone ngrok tunnel launcher (for local/Colab dev only)
├── requirements.txt      # Python package dependencies
├── dockerfile            # Docker image build definition
├── docker-compose.yml    # Multi-container orchestration (line-bot + ngrok)
├── entrypoint.sh         # Container startup script (git pull + uvicorn)
├── nginx.conf            # Nginx config (reserved; not wired in docker-compose)
├── text.txt              # Scratch/notes file
├── Line_Asst.ipynb       # Jupyter notebook (development/test scratchpad)
└── document/
    └── tech-spec.md      # This document
```

### File Responsibilities

#### `main.py`
The single source of truth for application behaviour. Contains:
- FastAPI app initialisation and endpoint definitions (`/`, `/webhook`, `/health`)
- `WebhookHandler` registration for LINE events
- **Session state machine** — `user_sessions: Dict[str, Dict]` keyed by LINE `user_id`
- Text message handler (`handle_text_message`) — routes conversation based on current session state
- Image message handler (`handle_image_message`) — triggers OCR or damage analysis based on state
- Helper functions: `extract_phone_from_response`, `process_search_result`, `extract_info_from_image_with_gemini`, `analyze_damage_with_gemini`

#### `flex_messages.py`
Stateless functions that return `FlexContainer` objects for LINE:
- `create_request_info_flex()` — prompt user to identify themselves
- `create_vehicle_selection_flex(policies)` — carousel when multiple policies found
- `create_policy_info_flex(policy_info)` — display matched policy details
- `create_analysis_result_flex(...)` — damage analysis result with optional call button
- `create_additional_info_prompt_flex()` — optional incident description prompt
- `create_input_method_flex()` — (unused in current main flow) selection of input method

#### `mock_data.py`
Provides a hardcoded `MOCK_POLICIES` dict and three lookup functions:
- `search_policies_by_cid(cid: str) -> List[Dict]`
- `search_policies_by_plate(plate: str) -> Optional[Dict]`
- `search_policies_by_name(name: str) -> List[Dict]`

> **Important:** This module is the integration boundary for a real database. When connecting to production data, replace only this module without changing `main.py`.

#### `entrypoint.sh`
Used as the Docker container CMD. On first boot clones the repository; on subsequent boots pulls the latest commit. This enables **code updates without rebuilding the Docker image** by restarting the container.

---

## 5. Environment Variables

All variables are loaded from a `.env` file (via `python-dotenv`) and must be present before the app starts. Missing variables cause an immediate `ValueError` on startup.

| Variable | Required | Description |
|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | LINE Messaging API channel access token |
| `LINE_CHANNEL_SECRET` | ✅ | LINE Messaging API channel secret (for webhook signature verification) |
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key for Gemini access |
| `NGROK_AUTHTOKEN` | ✅ (Docker) | ngrok authentication token for the ngrok container |
| `PORT` | ❌ | Uvicorn listen port. Defaults to `8000` |
| `REPO_URL` | ✅ (entrypoint) | Git repository URL used by `entrypoint.sh` for auto-pull |
| `BRANCH` | ✅ (entrypoint) | Git branch to checkout in `entrypoint.sh` |

### `.env` File Template

```dotenv
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
GEMINI_API_KEY=your_gemini_api_key
NGROK_AUTHTOKEN=your_ngrok_auth_token

# Optional
PORT=8000
REPO_URL=https://github.com/your-org/line-asst.git
BRANCH=main
```

> **Security:** Never commit `.env` to version control. Add it to `.gitignore`.

---

## 6. API Endpoints

### `GET /`
Health probe. Returns application name, status, and version.

```json
{
  "message": "LINE Insurance Claim Bot API",
  "status": "running",
  "version": "1.0.0"
}
```

### `POST /webhook`
The LINE platform sends all user events here. The handler verifies the `X-Line-Signature` header using `LINE_CHANNEL_SECRET`. On signature mismatch, returns `HTTP 400`. Delegates events to registered `@handler.add` callbacks.

**Request Headers:**
| Header | Description |
|---|---|
| `X-Line-Signature` | HMAC-SHA256 signature computed by LINE over the request body |
| `Content-Type` | `application/json` |

**Response:** `{"status": "ok"}` with `HTTP 200`

**Error Cases:**
| Condition | HTTP Status |
|---|---|
| Missing `X-Line-Signature` | 400 |
| Invalid signature | 400 |
| Internal processing error | 500 |

### `GET /health`
Detailed health check. Reports whether required credentials are configured.

```json
{
  "status": "healthy",
  "line_configured": true,
  "gemini_configured": true
}
```

---

## 7. User Conversation Flow (State Machine)

Each user's progress is tracked in the `user_sessions` dictionary using their LINE `user_id` as the key. The session stores the current `state` string plus contextual data accumulated across steps.

### State Diagram

```
[Any State / No Session]
        │  User sends "เช็คสิทธิ์เคลมด่วน"
        ▼
waiting_for_info
        │  User sends: text (name / plate / 13-digit CID)
        │              OR image (ID card / license plate photo)
        │
        ├─── Single policy found ──────────────────────────────────┐
        │                                                          ▼
        └─── Multiple policies found ──► waiting_for_vehicle_selection
                                                 │  User taps "เลือกทะเบียน <plate>"
                                                 │
                                                 └────────────────────────────────────┐
                                                                                      ▼
                                                                          waiting_for_counterpart
                                                                                      │
                                                                    User replies "มีคู่กรณี"
                                                                    or "ไม่มีคู่กรณี"
                                                                                      ▼
                                                                     waiting_for_additional_info
                                                                                      │
                                                                   User types incident description
                                                                   or sends "ข้าม"
                                                                                      ▼
                                                                          waiting_for_image
                                                                                      │
                                                                    User sends damage photo
                                                                                      ▼
                                                                              [AI Analysis]
                                                                                      │
                                                                                      ▼
                                                                                 completed
```

### Session Data Structure

```python
user_sessions: Dict[str, Dict] = {
    "<user_id>": {
        "state": str,                   # Current state (see above)
        "policy_info": Dict,            # Selected policy record from mock_data
        "has_counterpart": str,         # "มีคู่กรณี" | "ไม่มีคู่กรณี"
        "additional_info": str | None,  # Optional incident description
        "search_results": List[Dict],   # Populated only in waiting_for_vehicle_selection
    }
}
```

### State Transition Table

| Current State | Input Trigger | Next State | Bot Response |
|---|---|---|---|
| *(none / any)* | `"เช็คสิทธิ์เคลมด่วน"` | `waiting_for_info` | `create_request_info_flex()` |
| `waiting_for_info` | Text: 13-digit CID | `waiting_for_counterpart` or `waiting_for_vehicle_selection` | Policy Flex or vehicle selector |
| `waiting_for_info` | Text: license plate | `waiting_for_counterpart` | Policy Flex + counterpart QuickReply |
| `waiting_for_info` | Text: name | `waiting_for_counterpart` or `waiting_for_vehicle_selection` | As above |
| `waiting_for_info` | Image (ID card / plate) | `waiting_for_counterpart` or `waiting_for_vehicle_selection` | OCR result → same as text path |
| `waiting_for_vehicle_selection` | `"เลือกทะเบียน <plate>"` | `waiting_for_counterpart` | Policy Flex + counterpart QuickReply |
| `waiting_for_counterpart` | `"มีคู่กรณี"` or `"ไม่มีคู่กรณี"` | `waiting_for_additional_info` | `create_additional_info_prompt_flex()` |
| `waiting_for_additional_info` | Any text (or `"ข้าม"`) | `waiting_for_image` | Prompt to send damage photo |
| `waiting_for_image` | Image (damage photo) | `completed` | AI analysis result Flex or Text |
| `completed` | Any text | *(unchanged)* | Welcome message with prompt to restart |

> **Note:** In `waiting_for_info`, image messages are handled through a push-message path because the reply token is consumed by the immediate "กำลังค้นหา..." acknowledgement.

---

## 8. Core Modules

### 8.1 `extract_info_from_image_with_gemini(image_bytes)`

**Purpose:** OCR — detects whether an image is an **ID card** or **license plate** and extracts the relevant value.

**Process:**
1. Open image bytes with `PIL.Image`.
2. Build a structured prompt asking Gemini to return JSON `{"type": "...", "value": "..."}`.
3. Call `gemini_model.generate_content([prompt, img])`.
4. Parse the JSON from the response using `re.search(r'\{.*\}', ...)`.

**Returns:**
```python
{"type": "id_card", "value": "1234567890123"}
# OR
{"type": "license_plate", "value": "1กข1234"}
# OR
{"type": "unknown", "value": None}
```

**Error Handling:** Catches all exceptions, returns `{"type": "unknown", "value": None}`.

---

### 8.2 `analyze_damage_with_gemini(image_bytes, policy_info, additional_info, has_counterpart)`

**Purpose:** Multi-modal AI analysis — compares a damage photo against the policyholder's actual PDF policy document, then produces a structured claim eligibility verdict in Thai.

**Process:**
1. Check that `policy_info['policy_document_base64']` is present; return error string if not.
2. Construct a detailed Thai-language system prompt embedding:
   - Policyholder name, vehicle, insurance company
   - Counterpart status (`has_counterpart`)
   - Optional incident description (`additional_info`)
   - Structured output format with sections for policy data, damage analysis, eligibility verdict, cost summary, and next steps
3. Open damage image with `PIL.Image`.
4. Decode the Base64 policy PDF to bytes.
5. Write PDF to a `tempfile.NamedTemporaryFile`.
6. Upload PDF to Gemini Files API via `genai.upload_file(path, mime_type="application/pdf")`.
7. Wait 2 seconds for Gemini to process the file.
8. Call `gemini_model.generate_content([system_prompt, damage_image, uploaded_pdf])`.
9. Delete the uploaded file from Gemini and the local temp file.

**Returns:** Thai-language analysis string.

**Claim Eligibility Logic Embedded in Prompt:**
| Insurance Class | With Counterpart | Without Counterpart |
|---|---|---|
| ชั้น 1 | ✅ Claimable | ✅ Claimable |
| ชั้น 2+ / 2 | ✅ Claimable | ❌ Not claimable |
| ชั้น 3+ / 3 | ✅ Claimable | ❌ Not claimable |

---

### 8.3 `extract_phone_from_response(text)`

**Purpose:** Parses the AI analysis result to find a Thai insurance hotline number using regex patterns.

**Supported Patterns:**
- `โทร 1557` → `"1557"`
- `โทร 02-123-4567` → `"021234567"`
- `เบอร์: 098-765-4321` → `"0987654321"`
- `โทรศัพท์: 02-123-4567`
- `แจ้งเหตุ 1557`
- `โทร: 0987654321`

**Returns:** Phone number string (digits only, no dashes/spaces), or `None` if not found. Used to conditionally render a dial button in the result Flex Message.

---

### 8.4 `process_search_result(line_bot_api, event, user_id, policies, use_push=False)`

**Purpose:** Centralises the post-search response logic used by both text and image input paths.

**Behaviour:**
- `policies` is empty → Send "not found" text message.
- `policies` has 1 item → Set state to `waiting_for_counterpart`, send policy Flex + counterpart QuickReply.
- `policies` has >1 items → Set state to `waiting_for_vehicle_selection`, send carousel with one bubble per policy.

**`use_push` parameter:** When `True`, uses `push_message` (for image handler path where reply token is already consumed); when `False`, uses `reply_message`.

---

## 9. Data Model

### Policy Record (`Dict`)

```python
{
    "policy_number":           str,   # e.g. "POL-2024-001234"
    "title_name":              str,   # e.g. "นาย", "นาง", "นางสาว"
    "first_name":              str,   # May contain trailing space — use .strip()
    "last_name":               str,
    "cid":                     str,   # 13-digit national ID
    "plate":                   str,   # e.g. "1กข1234"
    "car_model":               str,   # e.g. "Toyota Camry 2.5 Hybrid"
    "car_year":                str,   # e.g. "2023"
    "insurance_type":          str,   # e.g. "ชั้น 1", "ชั้น 2+", "ชั้น 3+"
    "insurance_company":       str,   # Full company name
    "policy_start":            str,   # "DD/MM/YYYY"
    "policy_end":              str,   # "DD/MM/YYYY"
    "status":                  str,   # "active" | "expired"
    "policy_document_base64":  str | None  # Base64-encoded PDF; None means no document loaded
}
```

### `MOCK_POLICIES` Dict Key Format

The current mock uses a composite string key: `"<title_name><first_name> <last_name>_<plate>"`.  
This is an **internal implementation detail** — all lookups go through the three search functions, not direct dict access.

### Search Functions (`mock_data.py`)

| Function | Lookup Key | Match Strategy | Returns |
|---|---|---|---|
| `search_policies_by_cid(cid)` | `record["cid"]` | Exact string match | `List[Dict]` |
| `search_policies_by_plate(plate)` | `record["plate"]` | Exact string match | `Optional[Dict]` |
| `search_policies_by_name(name)` | `record["first_name"]` + `record["last_name"]` | Partial substring match on combined name | `List[Dict]` |

> **Production Integration:** Replace the body of these three functions with database queries or REST API calls. The function signatures must remain unchanged to avoid touching `main.py`.

---

## 10. AI Integration (Google Gemini)

### Model

```python
gemini_model = genai.GenerativeModel(model_name='models/gemini-2.5-flash')
```

### Two Use Cases

| Use Case | Function | Input | Output |
|---|---|---|---|
| OCR | `extract_info_from_image_with_gemini` | PIL Image | JSON dict |
| Damage Analysis | `analyze_damage_with_gemini` | PIL Image + Gemini File (PDF) | Thai text string |

### File Upload Lifecycle (PDF Policy Documents)

```
1. Decode Base64 → bytes
2. Write to tempfile (suffix='.pdf')
3. genai.upload_file(path, mime_type="application/pdf")
4. time.sleep(2)  ← wait for Gemini to index file
5. generate_content([prompt, damage_image, uploaded_file])
6. genai.delete_file(uploaded_file.name)  ← clean up Gemini storage
7. os.unlink(temp_pdf_path)               ← clean up local temp
```

> **Important:** Step 6 (delete from Gemini) runs in a `try/finally` to ensure temp files are always cleaned up even on error.

### Gemini API Error Handling

Both AI functions wrap all Gemini calls in `try/except Exception`. On error, `analyze_damage_with_gemini` returns a user-facing Thai error string rather than raising, allowing the bot to gracefully inform the user.

---

## 11. LINE Flex Message UI Components

All components are defined in `flex_messages.py`. Each function returns a `FlexContainer` built from a plain `dict` via `FlexContainer.from_dict(flex_message)`.

| Function | Type | Trigger |
|---|---|---|
| `create_request_info_flex()` | Bubble | Session start ("เช็คสิทธิ์เคลมด่วน") |
| `create_vehicle_selection_flex(policies)` | Carousel | Multiple policies found |
| `create_policy_info_flex(policy_info)` | Bubble | Single policy found or vehicle selected |
| `create_additional_info_prompt_flex()` | Bubble | After counterpart answer |
| `create_analysis_result_flex(summary_text, phone_number, insurance_company, claim_status)` | Bubble (mega) | After AI analysis completes |
| `create_input_method_flex()` | Bubble | *Available but not wired into current main flow* |

### Colour Codes Used

| Colour | Hex | Usage |
|---|---|---|
| Blue | `#0066FF` | Primary action, header backgrounds |
| Green | `#00B900` | Policy found confirmation |
| Orange | `#FF6B00` | Multiple vehicles found warning |
| Red | `#FF0000` | Unclaimable verdict |
| Gold | `#FFA500` | Claimable with excess warning |

---

## 12. Deployment

### Docker Compose Services

#### `line-bot` service

```yaml
build: .             # Built from ./dockerfile
container_name: line-bot
env_file: .env       # All env vars from .env file
expose: ["8000"]     # Internal only — not published to host
restart: always
```

#### `ngrok` service

```yaml
image: ngrok/ngrok:latest
command: ["http", "line-bot:8000", "--log=stdout"]
environment:
  - NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
ports:
  - "4040:4040"      # ngrok dashboard accessible on host
depends_on:
  - line-bot
restart: always
```

### Docker Build (`dockerfile`)

```
Base: python:3.11-slim
- Install ca-certificates (needed for SSL to Gemini API)
- Set SSL_CERT_FILE env var
- pip install -r requirements.txt
- COPY . .
- CMD: python main.py
```

### Startup Commands

```bash
# Build and start all services
docker compose up -d --build

# View ngrok public URL
docker compose logs ngrok | grep "url="

# View application logs
docker compose logs -f line-bot

# Stop all services
docker compose down
```

### Webhook Registration

1. After `docker compose up`, get the ngrok public URL from the ngrok dashboard at `http://localhost:4040`.
2. In the [LINE Developers Console](https://developers.line.biz/), set the Webhook URL to:
   ```
   https://<ngrok-subdomain>.ngrok-free.app/webhook
   ```
3. Enable webhook and disable auto-reply/greeting messages.

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file first)
# Start application
python main.py

# In a separate terminal, launch ngrok tunnel (uses ngrok.py standalone script)
python ngrok.py
```

> **Note:** `ngrok.py` uses `pyngrok` library, which is commented out in `requirements.txt` (`#pyngrok`). Install it separately for local dev: `pip install pyngrok`.

---

## 13. Known Limitations & Future Work

### Current Limitations

| # | Limitation | Impact | Recommendation |
|---|---|---|---|
| 1 | **In-memory session storage** | Sessions lost on restart; no persistence; no horizontal scaling | Replace with Redis or a shared cache |
| 2 | **Mock policy data** (`mock_data.py`) | No real policy data; hardcoded test records only | Implement database integration (PostgreSQL / MySQL) or connect to policy management API |
| 3 | **No session expiry** | Sessions accumulate indefinitely in memory for inactive users | Add TTL expiry (e.g., 30 minutes) using a timestamp + background cleanup task |
| 4 | **PDF dependency for AI analysis** | If `policy_document_base64` is `None`, analysis is blocked entirely | Consider fallback to text-based analysis using policy metadata fields |
| 5 | **2-second hardcoded sleep for Gemini file processing** | Brittle — large PDFs may need more time; small PDFs waste time | Implement polling via `genai.get_file()` until state is `ACTIVE` |
| 6 | **ngrok free tier** | URL changes on every restart; free tier has connection limits | Use a paid ngrok plan, a static domain, or replace with a reverse proxy on a fixed IP |
| 7 | **No rate limiting** | Malicious users could spam the bot and incur Gemini API costs | Add per-user request rate limiting |
| 8 | **Single-process, no async AI calls** | Long AI analysis (10–30s) blocks the handler thread | Move Gemini calls to a background task / queue (e.g., Celery, FastAPI `BackgroundTasks`) |
| 9 | **`nginx.conf` present but unused** | docker-compose does not start an nginx container | Integrate nginx as a reverse proxy in front of uvicorn for production hardening |
| 10 | **`first_name` trailing space** | `policy_info['first_name']` has a trailing space — `.strip()` must be called manually | Clean data at source / normalise on ingestion |

### Recommended Production Enhancements

1. **Database:** Replace `mock_data.py` with SQLAlchemy or an ORM connecting to a relational database. Policy documents (PDFs) should be stored in object storage (e.g., S3, GCS) and referenced by URL rather than stored as Base64 strings in the database.
2. **Session persistence:** Use Redis with TTL for `user_sessions`.
3. **Async Gemini calls:** Wrap `analyze_damage_with_gemini` as a `BackgroundTask` and use Push Messages to deliver results, which is already partially implemented.
4. **Logging:** Replace `print()` statements with `logging` module and a structured log aggregator.
5. **Monitoring:** Integrate with Sentry or similar for exception tracking.
6. **CI/CD:** Set up a pipeline to build and push a Docker image on merge to main; remove the `entrypoint.sh` git-pull pattern in favour of image tags.
7. **Scalability:** The current `user_sessions` dict and single-process model must be replaced before multi-instance deployment.
