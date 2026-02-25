# Insurance Claims AI Chatbot — Complete Technical Specification

> **Version:** 1.0 MVP  
> **Last Updated:** 2026-02-16  
> **Purpose:** Full technical specification sufficient for another AI agent to rebuild the entire system from scratch.

---

## 1. Product Overview

### 1.1 What It Does

An AI-powered chatbot that helps insurance customers file claims through a conversational web interface. Customers describe their situation in Thai or English, upload required documents (photos of IDs, receipts, damage, etc.), and the AI categorizes, extracts data from, and validates all documents before submitting the claim. Separate web dashboards let reviewers manage claims and managers monitor performance.

### 1.2 Supported Claim Types

| Code | Claim Type         | Thai Name             |
|------|--------------------|-----------------------|
| `CD` | Car Damage         | เคลมประกันรถยนต์       |
| `H`  | Health             | เคลมประกันสุขภาพ       |

### 1.3 User Roles (No Authentication)

| Role       | URL Path     | Purpose                                        |
|------------|-------------|------------------------------------------------|
| Customer   | `/`         | Chat with AI, upload documents, submit claims   |
| Reviewer   | `/reviewer` | Review claims, mark document usefulness, update status |
| Manager    | `/manager`  | View statistics, response times, accuracy rates |
| Admin      | `/admin`    | View application logs, change log level, monitor tokens |

---

## 2. Technology Stack

### 2.1 Backend
- **Framework:** FastAPI (Python 3.12)
- **AI/Vision:** Azure OpenAI SDK (`openai` Python package) — GPT-4 Vision deployment
- **Image Processing:** Pillow (PIL) for EXIF/GPS extraction
- **Data Formats:** YAML (`PyYAML`) for claim status, JSON for extracted data
- **Web Server:** Uvicorn
- **Environment:** python-dotenv for `.env` loading

### 2.2 Frontend
- **Technology:** Vanilla HTML + CSS + JavaScript (no framework)
- **Typography:** Google Fonts — Inter
- **Design:** Dark theme with CSS custom properties, glassmorphism effects
- **Charts:** Chart.js (CDN-loaded in manager dashboard)

### 2.3 Infrastructure
- **Container:** Docker with single Dockerfile (python:3.12-slim base)
- **Orchestration:** docker-compose.yml
- **Persistence:** Docker volume mapping `~/ntl-hackaton/data:/claims`
- **Port:** 8000

### 2.4 Python Dependencies (`backend/requirements.txt`)
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
pydantic>=2.5.0
openai>=1.12.0
Pillow>=10.0.0
PyYAML>=6.0
python-dotenv>=1.0.0
aiofiles>=23.2.0
```

### 2.5 Environment Variables (`.env`)
```
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_API_KEY=<your_key>
AZURE_OPENAI_DEPLOYMENT=gpt-4-vision     # Deployment name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

---

## 3. Architecture

### 3.1 Project Directory Structure
```
/
├── backend/
│   ├── main.py              # FastAPI app, all API endpoints
│   ├── models.py            # Pydantic data models
│   ├── gemini_service.py    # AI/Vision: chat, categorize, extract, ID extraction
│   ├── claim_service.py     # Claim CRUD, file storage, sequence numbers
│   ├── policy_service.py    # Policy verification from JSON database
│   ├── logging_service.py   # Structured logging with persistence
│   ├── token_tracking.py    # AI token usage & cost tracking
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Customer chat page
│   ├── chat.js              # Chat logic, document upload, state management
│   ├── styles.css           # Shared styles (design system, dark theme)
│   ├── reviewer.html        # 3-column reviewer dashboard
│   ├── reviewer.css         # Reviewer-specific styles
│   ├── reviewer.js          # Reviewer logic (thumbnails, preview, extracted data)
│   ├── manager.html         # Manager statistics dashboard
│   ├── manager.css          # Manager-specific styles
│   ├── manager.js           # Chart.js charts, statistics display
│   ├── admin.html           # Admin log viewer
│   ├── admin.css            # Admin-specific styles
│   └── admin.js             # Log search, level control, token monitoring
├── data/
│   ├── health_policies.json # Health policy database (5 records)
│   └── car_policies.json    # Car policy database (5 records)
├── Dockerfile
├── docker-compose.yml
└── .env
```

### 3.2 Data Storage Structure (Runtime — `/claims`)
```
/claims/
├── sequence.json                     # Persisted sequence numbers {"CD": N, "H": N}
├── logs.json                         # Persisted application logs (max 2000 entries)
├── token_usage.json                  # Persisted token usage records
├── app.log                           # Text log file
├── CD-20260129-000001/               # Car damage claim folder
│   ├── status.yaml                   # Status, memo, documents, metrics
│   ├── extracted_data.json           # All AI-extracted data from documents
│   ├── summary.md                    # Claim summary
│   └── documents/
│       ├── driving_license_20260129_120000.jpg
│       ├── vehicle_registration_20260129_120015.png
│       ├── vehicle_damage_photo_20260129_120030.jpg
│       └── vehicle_location_photo_20260129_120045.webp
└── H-20260129-000021/                # Health claim folder
    ├── status.yaml
    ├── extracted_data.json
    ├── summary.md
    └── documents/
        ├── medical_certificate_20260129_154515.png
        ├── citizen_id_card_20260129_154523.jpg
        ├── receipt_20260129_154531.jpg
        └── itemized_bill_20260129_154613.png
```

---

## 4. Data Models (`models.py`)

### 4.1 Enums
```python
class ClaimType(str, Enum):
    CAR_DAMAGE = "CD"
    HEALTH = "H"

class ClaimStatus(str, Enum):
    SUBMITTED = "Submitted"
    UNDER_REVIEW = "Under Review"
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    PAID = "Paid"
```

### 4.2 Core Models

#### ChatRequest / ChatResponse
```python
class ChatRequest(BaseModel):
    message: str
    session_id: str
    claim_id: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    claim_id: Optional[str] = None
    claim_type: Optional[ClaimType] = None
    required_documents: Optional[List[str]] = None
    missing_documents: Optional[List[str]] = None
    is_complete: bool = False
    response_time_ms: int
```

#### Document-Related Models
```python
class DocumentInfo(BaseModel):
    filename: str
    category: str
    useful: Optional[bool] = None      # Reviewer marks useful/not-useful
    uploaded_at: datetime

class DrivingLicenseData(BaseModel):
    name_th: Optional[str] = None
    name_en: Optional[str] = None
    license_id: Optional[str] = None   # 8-digit license number
    citizen_id: Optional[str] = None   # 13-digit Thai ID
    date_of_birth: Optional[str] = None  # YYYY-MM-DD (converted from Buddhist Era)
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None

class VehicleRegistrationData(BaseModel):
    plate_number: Optional[str] = None
    province: Optional[str] = None
    vehicle_type: Optional[str] = None
    registration_date: Optional[str] = None
    brand: Optional[str] = None
    chassis_number: Optional[str] = None   # 17-character
    engine_number: Optional[str] = None
    model_year: Optional[str] = None       # Gregorian year

class DamagePhotoData(BaseModel):
    filename: str
    gps_latitude: Optional[float] = None   # Extracted from EXIF
    gps_longitude: Optional[float] = None
    gps_location: Optional[str] = None
    taken_at: Optional[str] = None

class CitizenIdCardData(BaseModel):
    name_th: Optional[str] = None
    name_en: Optional[str] = None
    citizen_id: Optional[str] = None     # 13-digit
    date_of_birth: Optional[str] = None  # YYYY-MM-DD
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None

class MedicalReceiptData(BaseModel):
    disease: Optional[str] = None
    total_paid_amount: Optional[float] = None
    paid_date: Optional[str] = None
    hospital_name: Optional[str] = None
    billing_number: Optional[str] = None
    paid_items: Optional[List[PaidItem]] = None  # [{item: str, amount: float}]
```

#### Claim & Statistics Models
```python
class Claim(BaseModel):
    claim_id: str
    claim_type: ClaimType
    status: ClaimStatus
    memo: str = ""
    created_at: datetime
    documents: List[DocumentInfo] = []
    extracted_data: Optional[Dict[str, Any]] = None
    total_paid_amount: Optional[float] = None
    avg_response_time_ms: Optional[float] = None

class DailyStats(BaseModel):
    date: str           # YYYY-MM-DD
    cd_claims: int = 0
    h_claims: int = 0
    cd_paid_amount: float = 0
    h_paid_amount: float = 0

class StatsResponse(BaseModel):
    daily_stats: List[DailyStats]
    total_claims: int
    avg_response_time_ms: float
    accuracy_rate: float          # Percentage of useful documents
    total_cd_paid: float
    total_h_paid: float
```

---

## 5. API Endpoints (`main.py`)

### 5.1 Page Serving

| Method | Path         | Description                         |
|--------|-------------|-------------------------------------|
| GET    | `/`         | Customer chat page (`index.html`)    |
| GET    | `/reviewer` | Reviewer dashboard (`reviewer.html`) |
| GET    | `/manager`  | Manager dashboard (`manager.html`)   |
| GET    | `/admin`    | Admin dashboard (`admin.html`)       |

Static assets served from `/static/` → `frontend/` directory.

### 5.2 Chat & Session APIs

#### `POST /api/session/new`
Creates a new chat session. Returns `{ session_id: string }`.

**Session structure (in-memory):**
```json
{
  "claim_type": null,
  "claim_id": null,
  "messages": [],
  "uploaded_docs": [],
  "policy_verified": false,
  "policy_info": null,
  "id_card_number": null
}
```

#### `GET /api/session/{session_id}`
Returns session data including `claim_id`, `claim_type`, `messages`, `uploaded_docs`.

#### `POST /api/chat`
**Request:** `ChatRequest { message, session_id, claim_id? }`

**Business Logic:**
1. Retrieve or create session
2. If no `claim_type` detected yet → call `detect_claim_type(message)` using keyword matching
3. If claim type detected → auto-create claim via `claim_service.create_claim()`
4. Build context string with claim type, ID, and uploaded docs
5. Call Azure OpenAI for chat response
6. Record response time metrics
7. Return `ChatResponse` with required/missing documents list

**Claim Type Detection Keywords:**
- **Car:** `รถ, ชน, เฉี่ยว, ขโมย, หาย, car, vehicle, accident, damage, crash`
- **Health:** `เจ็บ, ป่วย, ผ่าตัด, โรง, พยาบาล, health, sick, hospital, medical, surgery`
- Uses keyword scoring — higher match count wins; returns `None` if tied (bot asks for clarification)

### 5.3 Policy Verification

#### `POST /api/verify-policy`
**Form fields:** `session_id`, `claim_type`, `id_number?`, `file?` (image upload)

**Business Logic:**
1. Accept either typed 13-digit ID number OR image of ID card/driving license
2. If image provided → call `extract_id_card_number()` with AI Vision to extract 13 digits
3. Validate extracted ID is exactly 13 digits
4. Call `policy_service.verify_policy(id_number, claim_type_key)`
5. Look up in `health_policies.json` or `car_policies.json`
6. Check: exists? → active status? → date range valid (start ≤ today ≤ end)?
7. Return policy details or appropriate error message
8. Store policy info in session on success

**Verification Results:**
- `found=True, status=active` → Policy valid, returns coverage details
- `found=True, status=expired` → Policy expired
- `found=True, status=inactive` → Policy not active
- `found=False` → No matching policy

### 5.4 Document Upload & Processing

#### `POST /api/upload`
**Form fields:** `file` (image), `session_id`, `claim_id?`

**Business Logic (critical flow):**
1. Read file content as bytes
2. **Categorize** → call AI Vision `categorize_document()` to identify document type
3. Handle special results:
   - `rate_limited` → return retry message
   - `unknown` → reject with re-upload instructions
4. Generate filename: `{category}_{YYYYMMDD_HHMMSS}{ext}`
5. Save to `/claims/{claim_id}/documents/`
6. **Extract data** → call AI Vision `extract_document_data()` with category-specific OCR prompts
7. **GPS extraction** → for damage/location photos, extract EXIF GPS from image bytes using Pillow
8. **Driving license owner confirmation** → for car damage claims, driving licenses require owner confirmation (customer vs. other party) before storing
9. Merge extracted data into `extracted_data.json` under correct key
10. Calculate `documents_status` (uploaded vs. required counts, missing list)
11. Return extracted data + document status

**Document Categories per Claim Type:**

| Car Damage (CD)              | Health (H)                    |
|------------------------------|-------------------------------|
| `driving_license`            | `medical_certificate`         |
| `vehicle_registration`       | `discharge_summary` (optional)|
| `vehicle_damage_photo`       | `itemized_bill`               |
| `vehicle_location_photo`     | `receipt`                     |
|                              | `citizen_id_card`             |

**Extracted Data Storage Keys (in `extracted_data.json`):**
```
Car Damage:
  driving_license_customer     → DrivingLicenseData
  driving_license_other_party  → DrivingLicenseData
  vehicle_registration         → VehicleRegistrationData
  damage_photos[]              → List[DamagePhotoData]
  pending_driving_license      → temp storage before owner confirmation

Health:
  citizen_id_card              → CitizenIdCardData
  medical_certificate          → extracted fields
  itemized_bill                → extracted fields (items array)
  discharge_summary            → extracted fields
  medical_receipts[]           → List[MedicalReceiptData]  (multiple allowed)
```

#### `POST /api/upload/confirm-owner`
**Form fields:** `session_id`, `claim_id`, `owner` ("customer" | "other_party")

Moves pending driving license data from `pending_driving_license` to either `driving_license_customer` or `driving_license_other_party`. Rejects if that owner type already has a document uploaded.

### 5.5 Claim Submission

#### `POST /api/claims/submit`
**JSON body:** `{ claim_id: string }`

**Business Logic:**
1. Verify all required documents are uploaded (via `calculate_documents_status`)
2. If incomplete → reject with list of missing documents
3. Update `claim.yaml` metadata with `status: "submitted"` and `submitted_at` timestamp
4. Return success with claim ID

**Required Documents Check:**
- **Car Damage:** `driving_license_customer` + `driving_license_other_party` + `vehicle_registration` + at least 1 damage photo
- **Health:** `medical_certificate` + `itemized_bill` + `receipt` + `citizen_id_card`

### 5.6 Claims Management

| Method | Path                                           | Description                      |
|--------|-------------------------------------------------|----------------------------------|
| GET    | `/api/claims`                                   | List all claims (filter: `?claim_type=CD\|H`) |
| GET    | `/api/claims/{claim_id}`                        | Get full claim details            |
| PATCH  | `/api/claims/{claim_id}`                        | Update status and/or memo         |
| POST   | `/api/claims/{claim_id}/documents/usefulness`   | Mark document useful/not-useful   |
| GET    | `/api/claims/{claim_id}/documents/{filename}`   | Get document image file           |

**Document Usefulness Update:**
```json
{ "filename": "receipt_20260129_154531.jpg", "useful": true }
```
Updates `status.yaml` → `documents.{filename}.useful = true|false`

### 5.7 Statistics

#### `GET /api/stats`
**Query params:** `claim_type?`, `start_date?`, `end_date?`

**Business Logic:**
1. Load all claims, filter by type and date range (date-only comparison, no time)
2. Group by date → calculate daily counts per claim type
3. **Paid amounts:** Only sum `total_paid_amount` for claims with `status == "Paid"`
4. **Accuracy rate:** `useful_count / (useful_count + not_useful_count) * 100`
5. **Avg response time:** Mean of all `response_times_ms` from claim metrics
6. Return `StatsResponse`

### 5.8 Admin / Logging APIs

| Method | Path                     | Description                    |
|--------|--------------------------|--------------------------------|
| GET    | `/api/admin/log-level`   | Get current log level           |
| POST   | `/api/admin/log-level`   | Set log level (debug/info/warning/error) |
| GET    | `/api/admin/logs`        | Search logs with filters        |
| GET    | `/api/admin/logs/stats`  | Get log statistics              |
| DELETE | `/api/admin/logs`        | Clear all logs                  |

### 5.9 Token Tracking APIs

| Method | Path                      | Description              |
|--------|---------------------------|--------------------------|
| GET    | `/api/admin/tokens/stats` | Overall token usage stats |
| GET    | `/api/admin/tokens/chart` | Chart data by period      |
| GET    | `/api/admin/tokens/by-claim` | Breakdown by claim ID  |

### 5.10 Health Check
`GET /health` → `{ status: "ok" }`

---

## 6. AI Service Business Logic (`gemini_service.py`)

### 6.1 Azure OpenAI Client Configuration
```python
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION
)
```
All API calls use `client.chat.completions.create()` with `model=AZURE_OPENAI_DEPLOYMENT`.

### 6.2 Chat Response Generation
- **System prompt:** Bilingual Thai/English insurance assistant
- **Behavior:** Asks for claim type clarification if unclear before requesting any documents
- **Temperature:** 0.7
- **Max tokens:** 1024
- **Rate limit handling:** Returns pre-defined Thai/English error messages on 429 errors

### 6.3 Document Categorization
- Sends image + prompt listing valid categories for the claim type
- Returns category key string (e.g., "driving_license", "receipt")
- Falls back to "unknown" if AI returns unrecognized category
- Returns "rate_limited" on 429 errors

### 6.4 Document Data Extraction
Each document category has a specialized Thai OCR prompt:

| Category                | Extraction Format                                               |
|------------------------|-----------------------------------------------------------------|
| `driving_license`       | name_th, name_en, license_id, citizen_id, dates (BE→CE conversion) |
| `vehicle_registration`  | plate_number, province, vehicle_type, brand, chassis_number, engine_number, model_year |
| `citizen_id_card`       | name_th, name_en, citizen_id (13-digit), dates (BE→CE)          |
| `receipt`               | disease, total_paid_amount, paid_date, hospital_name, billing_number, paid_items[] |
| `medical_certificate`   | patient_name, diagnosis, treatment, doctor_name, hospital, dates |
| `itemized_bill`         | items with amounts, total                                        |
| `discharge_summary`     | diagnosis, treatment, admission/discharge dates                  |
| `vehicle_damage_photo`  | damage_description, damage_location, severity (minor/moderate/severe) |
| `vehicle_location_photo`| location_description, road_conditions, weather_conditions         |

**Critical:** All prompts instruct the AI to:
- Convert Buddhist Era (พ.ศ.) dates to Gregorian (ค.ศ.) by subtracting 543
- Return ONLY valid JSON, no explanations
- Use `null` for unreadable fields

### 6.5 ID Card Number Extraction (`extract_id_card_number`)
- Specialized prompt in Thai for reading 13-digit ID from Thai National ID Card or Driving License
- Explicitly instructs: return complete 13 digits, no masking, no asterisks, no dashes
- Post-processing: strips non-digit characters, validates exactly 13 digits
- Returns `None` if extraction fails

### 6.6 GPS Extraction from Images
- Uses Pillow to read EXIF data from image bytes
- Extracts GPS latitude/longitude from EXIF GPSInfo tags
- Converts DMS (Degrees/Minutes/Seconds) to decimal degrees
- Returns `{ gps_latitude, gps_longitude }` or `None`

### 6.7 Claim Summary Generation
- Takes claim ID, extracted data, and claim type
- Generates markdown summary using AI
- Saves to `summary.md` in claim folder

---

## 7. Claim Service Business Logic (`claim_service.py`)

### 7.1 Claim ID Generation
**Format:** `{ClaimType}-{YYYYMMDD}-{NNNNNN}`

| Part          | Description              | Example          |
|---------------|--------------------------|------------------|
| ClaimType     | "CD" or "H"              | `CD`             |
| YYYYMMDD      | Current date              | `20260129`       |
| NNNNNN        | 6-digit sequence (padded) | `000001`         |

**Sequence Numbers:**
- Stored in `/claims/sequence.json` → `{"CD": 4, "H": 21}`
- Auto-increment per claim type
- Persist across restarts via file
- CD and H sequences are independent

### 7.2 Claim Creation
Creates folder structure:
1. `{claim_id}/documents/` directory
2. `status.yaml` — initial status "Submitted", empty memo, empty documents, empty metrics
3. `extracted_data.json` — empty JSON object
4. `summary.md` — markdown template with claim type and creation date

### 7.3 Document Storage
- Saves document bytes to `{claim_id}/documents/{filename}`
- Updates `status.yaml` → `documents.{filename}` with category, useful flag, and upload timestamp
- Filename format: `{category}_{YYYYMMDD_HHMMSS}{original_extension}`

### 7.4 Status YAML Structure
```yaml
status: Submitted
memo: ""
documents:
  driving_license_20260129_120000.jpg:
    category: driving_license
    useful: true           # Set by reviewer
    uploaded_at: "2026-01-29T12:00:00"
  receipt_20260129_120030.png:
    category: receipt
    useful: null            # Not yet reviewed
    uploaded_at: "2026-01-29T12:00:30"
metrics:
  response_times_ms: [1234, 2345, 3456]
  created_at: "2026-01-29T12:00:00"
  updated_at: "2026-01-29T12:05:00"
```

### 7.5 Claim Retrieval
- Reads `status.yaml` and `extracted_data.json`
- Calculates `total_paid_amount` from extracted receipt data
- Calculates `avg_response_time_ms` from metrics
- Returns full `Claim` model

---

## 8. Policy Service Business Logic (`policy_service.py`)

### 8.1 Policy Database
JSON files in `data/` directory:

**Health Policy Fields:**
```json
{
  "id_card_number": "3100701443816",
  "name_th": "สมชาย ใจดี",
  "name_en": "Somchai Jaidee",
  "phone": "081-234-5678",
  "policy_number": "H-2026-001234",
  "plan": "Gold Health Plus",
  "coverage_ipd": 500000,
  "coverage_opd": 30000,
  "room_per_night": 5000,
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "status": "active"
}
```

**Car Policy Fields:**
```json
{
  "id_card_number": "3100701443816",
  "name_th": "สมชาย ใจดี",
  "name_en": "Somchai Jaidee",
  "phone": "081-234-5678",
  "policy_number": "CD-2026-001234",
  "vehicle_plate": "กก 1234 กรุงเทพมหานคร",
  "vehicle_brand": "Toyota",
  "vehicle_model": "Camry 2.5 HV Premium",
  "vehicle_year": 2024,
  "vehicle_color": "White Pearl",
  "coverage_type": "ชั้น 1",
  "coverage_amount": 1000000,
  "deductible": 5000,
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "status": "active"
}
```

### 8.2 Verification Logic
1. Clean ID (remove spaces, dashes)
2. Search policies by `id_card_number` match
3. If found & `status == "active"` → check date range (`start_date ≤ today ≤ end_date`)
4. Return policy details with coverage info, or appropriate error

### 8.3 Test Data (5 records each)

| ID Card Number   | Name         | Health Plan       | Car Coverage | Status  |
|------------------|-------------|-------------------|-------------|---------|
| 3100701443816    | สมชาย ใจดี   | Gold Health Plus  | ชั้น 1 ฿1M   | active  |
| 1360000162627    | สมหญิง รักดี  | Platinum Health   | —           | active  |
| 1111222233334    | วิชัย สุขสันต์ | Silver Health    | ชั้น 2+ ฿500K | active  |
| 5555666677778    | มานะ พยายาม  | Gold (expired)    | ชั้น 3 (expired) | expired |
| 3100500123456    | ทดสอบ ระบบ   | Diamond Health Max | ชั้น 1 ฿3M  | active  |

---

## 9. Logging Service (`logging_service.py`)

### 9.1 Features
- **In-memory buffer:** `deque(maxlen=2000)` with thread-safe access
- **Persistent storage:** Saves to `/claims/logs.json`, loads on startup
- **Periodic save:** Every 10 log entries, auto-saves in background thread
- **Housekeeping:** On load, removes entries older than 7 days; caps at 2000 records
- **File logging:** Also writes to `/claims/app.log` as plain text
- **Structured entries:** timestamp, level, category, message, claim_id, session_id, details

### 9.2 Log Categories
`chat`, `upload`, `extraction`, `categorization`, `api`, `system`, `error`

### 9.3 Log Levels
`DEBUG`, `INFO`, `WARNING`, `ERROR` — runtime-changeable via admin API

---

## 10. Token Tracking Service (`token_tracking.py`)

### 10.1 Features
- Tracks every Azure OpenAI API call: input/output tokens, cost
- Operations: `chat`, `categorization`, `extraction`, `summary`
- Persisted to `/claims/token_usage.json` (keeps last 10,000 records)
- Pricing: $0.01/1K input tokens, $0.03/1K output tokens (approximate GPT-4 Vision)

### 10.2 Chart Data Periods
Supports grouping by: `hour` (24h), `day` (7d), `week` (4w), `month` (12m), `year` (3y)

---

## 11. Frontend Pages

### 11.1 Customer Chat (`/` → `index.html` + `chat.js` + `styles.css`)

**Features:**
- Chat interface with bot messages and user messages
- Claim type detection and badge display
- Policy verification step (type ID or upload ID photo)
- Document upload with category display and extracted data preview
- Driving license owner confirmation dialog (for Car Damage claims)
- Document status tracker (uploaded X/Y, missing list)
- Submit claim button (enabled when all docs uploaded)
- Cancel/restart claim via keywords (ยกเลิก, cancel, เริ่มใหม่, restart, etc.)
- Bilingual Thai/English display

**Chat State Management (JavaScript):**
```javascript
let sessionId, claimId, claimType;
let policyVerified = false;
let policyInfo = null;
let uploadedDocs = [];
```

**Extracted Data Display:**
- `formatExtractedValue()` function converts nested JSON to human-readable format
- Thai labels for common fields (patient_name → ชื่อผู้ป่วย, etc.)
- Currency formatting with ฿ symbol and commas
- Arrays (like itemized bill items) displayed as formatted lists

### 11.2 Reviewer Dashboard (`/reviewer` → 3-column layout)

**Layout:**
| Left Column (280px) | Center Column (flexible) | Right Column (200px)  |
|---------------------|--------------------------|----------------------|
| Search + Refresh 🔄  | Document Preview (large)  | Document Thumbnails   |
| Status/Type Filters  | Selected Doc Label        | Click to select doc   |
| Claims List          | Extracted Data Display    | Active state highlight|
| Active claim highlight | Useful/Not Useful buttons | Usefulness badge     |
|                      | Status dropdown + Memo    |                      |
|                      | Save Changes button       |                      |

**Features:**
- Claim list with search, status filter, type filter
- Refresh button to reload claims list
- Click claim → loads documents into right sidebar as thumbnails
- Click thumbnail → shows large preview in center + extracted data below
- Extracted data shown with Thai field labels, per-document view
- Useful/Not Useful toggle buttons per document
- Status update dropdown + memo textarea + save button
- Auto-selects first document when claim is selected

### 11.3 Manager Dashboard (`/manager`)

**Features:**
- Date range picker (default: last 30 days)
- Claim type filter (All, Car Damage, Health)
- Summary cards: Total Claims, Avg Response Time, Accuracy Rate, Paid Amounts
- Chart.js bar chart: daily claim counts (CD vs H side-by-side)
- Claims table with: Claim ID, Type, Status, Created, Paid Amount, Avg Response Time
- Click claim row → navigate to reviewer

**Accuracy Calculation:**
```
accuracy_rate = useful_documents / (useful_documents + not_useful_documents) × 100
```

### 11.4 Admin Dashboard (`/admin`)

**Features:**
- Log level selector (debug/info/warning/error) — changes at runtime
- Log statistics: total entries, count by level, count by category, errors last hour
- Log search: text query, filter by category/level/claim_id
- Log table: timestamp, level, category, message (expandable details)
- Token usage section: total tokens, total cost, today's tokens, active claims
- Token chart: usage over time with period selector
- Token by claim: breakdown table

---

## 12. Customer Claim Flow (End-to-End)

### 12.1 Car Damage Claim Flow
```
1. Customer sends message: "รถผมชน" / "my car crashed"
   → AI detects claim_type = CD, creates claim ID
   → AI asks for 4 required documents

2. Customer types 13-digit ID or uploads ID card photo
   → POST /api/verify-policy (extract ID if image)
   → Policy verified → show coverage details

3. Customer uploads driving license photo
   → AI categorizes: "driving_license"
   → AI extracts: name, license_id, citizen_id, dates
   → Bot asks: "เป็นของคุณ (ฝ่ายเรา) หรือ คู่กรณี?"
   → Customer clicks "ของลูกค้า (ฝ่ายเรา)"
   → POST /api/upload/confirm-owner (owner="customer")

4. Customer uploads 2nd driving license (other party)
   → Same categorize+extract flow
   → Confirm as "other_party"

5. Customer uploads vehicle registration
   → AI categorizes: "vehicle_registration"
   → AI extracts: plate_number, brand, chassis, engine

6. Customer uploads damage photo
   → AI categorizes: "vehicle_damage_photo"
   → AI extracts: damage_description, severity
   → GPS extracted from EXIF if available

7. Documents status: 4/4 ✅ Complete
   → Submit button enabled
   → Customer clicks submit
   → POST /api/claims/submit → success
```

### 12.2 Health Claim Flow
```
1. Customer: "ผมป่วย" / "I'm sick"
   → AI detects claim_type = H, creates claim ID
   → AI asks for ID verification first

2. ID verification (same as above)

3. Customer uploads medical certificate
   → AI categorizes + extracts diagnosis, treatment, doctor

4. Customer uploads receipt(s) - multiple allowed
   → AI extracts amounts, items, hospital

5. Customer uploads itemized bill
   → AI extracts individual line items with amounts

6. Customer uploads citizen ID card
   → AI extracts personal info

7. (Optional) Customer uploads discharge summary

8. Required docs complete → submit
```

---

## 13. Docker Deployment

### 13.1 Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY data/ ./data/
RUN mkdir -p /claims
ENV PYTHONUNBUFFERED=1
ENV CLAIMS_DIR=/claims
EXPOSE 8000
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 13.2 docker-compose.yml
```yaml
services:
  claims-bot:
    build: .
    container_name: insurance-claims-bot
    ports:
      - "8000:8000"
    volumes:
      - ~/ntl-hackaton/data:/claims    # Persist claims data
    environment:
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_OPENAI_DEPLOYMENT=${AZURE_OPENAI_DEPLOYMENT}
      - AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2024-02-15-preview}
      - CLAIMS_DIR=/claims
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 13.3 Run Commands
```bash
# Build and start
docker-compose up --build

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

---

## 14. Design System (CSS)

### 14.1 CSS Custom Properties (`styles.css`)
```css
/* Color palette — dark theme */
--bg-primary: #0a0a1a;
--bg-secondary: #151528;
--bg-tertiary: #1e1e36;
--text-primary: #e8e8ef;
--text-secondary: #9d9db5;
--accent-purple: #7c3aed;
--accent-cyan: #06b6d4;
--accent-pink: #ec4899;
--gradient-primary: linear-gradient(135deg, #7c3aed, #06b6d4);

/* Spacing & shapes */
--radius-sm: 6px;
--radius-md: 10px;
--radius-lg: 16px;

/* Effects */
--shadow-glow: 0 0 20px rgba(124, 58, 237, 0.3);
--transition-fast: all 0.2s ease;
```

### 14.2 Design Principles
- Dark glassmorphism theme throughout all pages
- Gradient accents for interactive elements
- Status badge colors: green (Approved/Paid), yellow (Pending/Under Review), red (Rejected), blue (Submitted)
- Responsive design principles
- Google Font "Inter" for all text

---

## 15. Important Business Rules

1. **Language:** Bot responds in both Thai and English in every message
2. **Sequence numbers:** 6-digit, zero-padded, separate per claim type, persisted to file
3. **Date conversion:** Thai documents use Buddhist Era (พ.ศ.) dates — must subtract 543 for Gregorian
4. **Driving license ownership:** For car damage claims, each uploaded driving license must be assigned to either "customer" or "other_party" — cannot have duplicates per side
5. **Multiple receipts:** Health claims allow multiple receipt uploads stored as array
6. **Document validation:** Unknown/unclear images are rejected with re-upload instructions
7. **Rate limiting:** All AI calls handle 429 errors gracefully with user-friendly retry messages
8. **Paid amount calculation:** Manager stats only sum `total_paid_amount` from claims with `status == "Paid"`
9. **Accuracy metric:** Calculated from reviewer's useful/not-useful markings
10. **Claim cancellation:** Customer can cancel via keywords in chat (ยกเลิก, cancel, stop, etc.)
11. **No authentication:** All endpoints are public (MVP scope)
12. **Persistence:** Claims data, logs, token usage, and sequence numbers all survive container restarts via Docker volume

---

## 16. Error Handling Patterns

1. **AI API failures:** Return pre-defined bilingual error messages, never expose raw errors
2. **Rate limits (429):** Specific handling with retry instructions in Thai/English
3. **File not found:** Return 404 HTTPException
4. **Invalid session:** Return 400 with descriptive message
5. **Incomplete claims:** Reject submission with list of missing documents
6. **Unrecognized documents:** Return "unknown" category with acceptable document list
