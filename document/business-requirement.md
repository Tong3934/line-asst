# Business Requirement Document (BRD)
## LINE Insurance Claims Bot — "เช็คสิทธิ์ & เคลมประกันด่วน"

**Document Version:** 2.0  
**Date:** February 2026  
**Status:** Draft  
**Owner:** Product Owner

---

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | February 2026 | Initial release — eligibility check only |
| 2.0 | February 2026 | Merged: document upload, AI data extraction, data storage, claim submission, reviewer & manager dashboards |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Problem & Opportunity](#2-business-problem--opportunity)
3. [Project Objectives](#3-project-objectives)
4. [Stakeholders](#4-stakeholders)
5. [Target Users & Roles](#5-target-users--roles)
6. [Supported Claim Types](#6-supported-claim-types)
7. [User Journey Overview](#7-user-journey-overview)
8. [Functional Requirements](#8-functional-requirements)
9. [Business Rules](#9-business-rules)
10. [Non-Functional Requirements](#10-non-functional-requirements)
11. [System Integrations](#11-system-integrations)
12. [Data Requirements](#12-data-requirements)
13. [Out of Scope](#13-out-of-scope)
14. [Assumptions & Constraints](#14-assumptions--constraints)
15. [Success Metrics (KPIs)](#15-success-metrics-kpis)
16. [Known Risks & Mitigations](#16-known-risks--mitigations)
17. [Glossary](#17-glossary)

---

## 1. Executive Summary

**Product Name:** เช็คสิทธิ์ & เคลมประกันด่วน (Quick Insurance Eligibility Check & Claim Submission)  
**Customer Interface:** LINE Messaging App (Chatbot)  
**Internal Interface:** Web dashboards for Reviewer and Manager roles

This product is an **AI-powered LINE chatbot** that guides insurance policyholders through the complete insurance claim journey — from checking eligibility all the way to submitting a fully documented claim — without leaving the LINE app.

The customer describes their situation, verifies their identity, then uploads the required documents (photos of ID cards, driving licenses, vehicle registration, damage photos, or medical documents). The AI **automatically categorises each photo and extracts key data from it**, validates completeness, and assembles the full claim package. Once all required documents are uploaded, the customer submits the claim with a single tap.

Internally, a **Reviewer web dashboard** lets claims staff review each document, confirm extracted data, and update claim status. A **Manager web dashboard** provides real-time analytics on volumes, accuracy rates, and paid amounts.

---

## 2. Business Problem & Opportunity

### The Problem

| Pain Point | Who Feels It | Description |
|---|---|---|
| **Long hotline wait times** | Customer | Calling the insurance hotline can take 10–30+ minutes during peak hours |
| **Uncertainty about coverage** | Customer | Customers do not know if their policy type and incident qualify for a claim |
| **Paper-heavy document submission** | Customer | Customers must physically visit a service center or mail documents |
| **Manual data re-entry** | Claims Staff | Staff manually type data from photos and scans into internal systems |
| **No visibility into document quality** | Claims Staff | Staff cannot easily flag which documents were useful or too unclear to process |
| **Fragmented analytics** | Manager | No single dashboard for claim volumes, accuracy, and amounts paid |

### The Opportunity

LINE is the most-used messaging app in Thailand (50M+ active users). Placing the entire claim experience inside LINE means:

- **Zero new app to install** — customers already have LINE
- **Camera always ready** — customers photograph documents at the scene of the incident
- **AI removes manual entry** — structured data extracted automatically from every photo
- **Faster first assessment** — reviewers receive a complete, pre-extracted claim package
- **Rich analytics** — structured data enables dashboards and process insights

---

## 3. Project Objectives

| # | Objective | Measurable Target |
|---|---|---|
| 1 | Let policyholders check claim eligibility instantly without calling | Eligibility verdict in < 45 seconds |
| 2 | Let policyholders submit a complete, documented claim through LINE | End-to-end submission in < 5 minutes |
| 3 | Automate data extraction from document photos | AI extraction ≥ 90% accuracy on key fields (name, ID, dates) — verified by reviewer spot-check |
| 4 | Reduce manual intake work for claims staff | 70% of submitted claims arrive with all fields pre-extracted |
| 5 | Provide real-time dashboards for reviewers and managers | Data available within 1 minute of submission |
| 6 | Support both Car Damage and Health claim types | Both types fully functional at launch |

---

## 4. Stakeholders

| Role | Team | Responsibility |
|---|---|---|
| **Product Owner** | Insurance Digital Team | Defines requirements, accepts deliverables |
| **Business Sponsor** | Head of Claims Operations | Approves budget, defines success criteria |
| **Customer** | Thai policyholders | Files claims via LINE chatbot |
| **Reviewer** | Claims Operations / Adjusters | Reviews documents, marks quality, updates status via web dashboard |
| **Manager** | Claims Operations Management | Monitors performance via analytics dashboard |
| **Admin** | IT / DevOps | Monitors logs, configuration, AI token costs |
| **IT / DevOps Team** | Technical Development | Builds, deploys, and maintains the system |
| **Compliance / Legal** | Risk & Compliance | Ensures AI outputs are disclaimed; data privacy compliance |
| **LINE Platform** | LINE Corporation | Messaging infrastructure and Messaging API |
| **AI Provider** | Google Gemini / Azure OpenAI GPT-4 Vision | AI model for OCR, categorisation, and damage analysis |

---

## 5. Target Users & Roles

### Role 1 — Customer (LINE Chatbot)

> A Thai insurance policyholder who has just had a vehicle accident or health event and wants to file a claim from their smartphone.

- **Interface:** LINE app
- **Can do:** Check eligibility, verify identity, upload documents, submit claim
- **Cannot do:** Access web dashboards

### Role 2 — Reviewer (Web Dashboard at /reviewer)

> A claims staff member who reviews submitted documents, verifies AI-extracted data, and moves the claim through the approval workflow.

- **Interface:** Web browser
- **Can do:** View claims, inspect document images, see AI-extracted data, mark Useful / Not Useful, update status, add memos

### Role 3 — Manager (Web Dashboard at /manager)

> A claims operations manager who monitors overall performance — volumes, accuracy, times, and paid amounts.

- **Interface:** Web browser
- **Can do:** View statistics, filter by date range and claim type, drill down to claims

### Role 4 — Admin (Web Dashboard at /admin)

> An IT staff member who monitors system health, logs, and AI token costs.

- **Interface:** Web browser
- **Can do:** Search logs, change log verbosity at runtime, view AI API usage and cost

---

## 6. Supported Claim Types

| Code | Claim Type | Thai Name | Sub-type | Required Documents |
|:---:|---|---|---|---|
| **CD** | Car Damage | เคลมประกันรถยนต์ | With other party (มีคู่กรณี) | Driving license (customer) + **Driving license (other party)** + Vehicle registration + ≥1 damage photo |
| **CD** | Car Damage | เคลมประกันรถยนต์ | No other party (ไม่มีคู่กรณี) — e.g. hit a pole, wall, or tree | Driving license (customer) + Vehicle registration + ≥1 damage photo |
| **H** | Health | เคลมประกันสุขภาพ | — | Citizen ID card + Medical certificate + Itemised bill + Receipt(s) |

**Optional documents:**
- CD: Vehicle location photo (with GPS if available in EXIF)
- H: Discharge summary

---

## 7. User Journey Overview

> For the full visual step-by-step journey see [user-journey.md](user-journey.md).

### High-Level Flow

```
Customer (LINE)                System                         Internal (Web)
───────────────────────────────────────────────────────────────────────────────
1. Trigger
   Type incident or            Detect claim type (CD / H)
   "เช็คสิทธิ์เคลมด่วน"  →   Generate Claim ID
                               Create claim folder & records
                          ↓
2. Identity verification  →   AI reads ID photo if sent (OCR)
   Type ID / upload photo      Verify against policy database
                               Display coverage details
                          ↓
3. Document upload         →   AI categorises each photo
   (one at a time until        AI extracts key data fields
    all required received)     Save image + extracted JSON
                               Show customer what was read
                               Prompt for next missing doc
                          ↓
4. Ownership confirmation  →   Car Damage only:
   "Mine" / "Other party"      Assign license to correct party
                               in extracted_data.json
                          ↓
5. All documents complete  →   Validate completeness
   Customer submits            Mark status = Submitted
                               Save final claim package
                          ↓                                ↓
6. Claim ID shown                              Reviewer opens claim
   to customer                                 Reviews docs + extracted data
                                               Marks Useful / Not Useful
                                               Updates status (Approved / Rejected / Paid)
                                                              ↓
                                               Manager views analytics
                                               Volumes, accuracy, amounts paid
```

---

## 8. Functional Requirements

### FR-01: Conversation Trigger & Claim Type Detection

| ID | Requirement |
|---|---|
| FR-01.1 | The bot MUST start a new session when the user describes an incident or sends "เช็คสิทธิ์เคลมด่วน" |
| FR-01.2 | The bot MUST detect the claim type automatically from keywords in the message |
| FR-01.3 | **Car Damage keywords:** รถ, ชน, เฉี่ยว, ขโมย, หาย, car, vehicle, accident, damage, crash |
| FR-01.4 | **Health keywords:** เจ็บ, ป่วย, ผ่าตัด, โรงพยาบาล, health, sick, hospital, medical, surgery |
| FR-01.5 | If both keyword sets match equally, the bot MUST ask the customer to clarify |
| FR-01.6 | On detection, the system MUST auto-generate a Claim ID and create the claim record immediately |
| FR-01.7 | **Claim ID format:** `{CD or H}-{YYYYMMDD}-{NNNNNN}` — 6-digit zero-padded sequence per claim type, persisted across restarts |
| FR-01.8 | Customer can cancel and restart at any time: ยกเลิก, cancel, เริ่มใหม่, restart |

---

### FR-02: Policy Verification

| ID | Requirement |
|---|---|
| FR-02.1 | After claim type is detected, the bot MUST request identity verification before accepting documents |
| FR-02.2 | The bot MUST accept a **typed 13-digit national ID number** |
| FR-02.3 | The bot MUST accept a **photo of a Thai national ID card or driving license** — AI reads the 13-digit ID automatically |
| FR-02.4 | AI OCR MUST return digits only — no asterisks, dashes, or masking |
| FR-02.5 | The system MUST check the ID against the policy database and respond with: (a) Valid active policy, (b) Expired, (c) Inactive, or (d) Not found |
| FR-02.6 | On a valid policy, the bot MUST display: policy number, coverage type, coverage amount, deductible, vehicle or health plan details |
| FR-02.7 | Document upload MUST only begin after successful policy verification |

---

### FR-03: Document Upload & AI Categorisation

| ID | Requirement |
|---|---|
| FR-03.1 | The bot MUST accept image uploads (JPG, PNG, WebP) |
| FR-03.2 | After each upload, the AI MUST automatically **categorise** the document (e.g., driving_license, receipt) |
| FR-03.3 | If the AI cannot determine type ("unknown"), it MUST reject the image and tell the user which types are accepted |
| FR-03.4 | After each successful upload, the bot MUST confirm which document was recognised |
| FR-03.5 | The bot MUST always show upload progress: documents received so far and what is still missing |
| FR-03.6 | **Car Damage — With other party:** driving_license_customer + driving_license_other_party + vehicle_registration + vehicle_damage_photo (≥1); optional: vehicle_location_photo |
| FR-03.6b | **Car Damage — No other party:** driving_license_customer + vehicle_registration + vehicle_damage_photo (≥1); optional: vehicle_location_photo |
| FR-03.7 | **Health required:** citizen_id_card, medical_certificate, itemised_bill, receipt (multiple allowed); optional: discharge_summary |

---

### FR-04: AI Data Extraction from Document Photos

After categorisation, the AI MUST extract the following fields per document type:

| Document | Extracted Fields |
|---|---|
| **Driving License** | Full name (Thai + English), 8-digit license number, 13-digit citizen ID, date of birth, issue date, expiry date |
| **Vehicle Registration** | License plate, province, vehicle type, brand, chassis number (17 chars), engine number, model year |
| **Citizen ID Card** | Full name (Thai + English), 13-digit citizen ID, date of birth, issue date, expiry date |
| **Receipt** | Hospital name, billing number, total paid, date, itemised list (item + amount per line) |
| **Medical Certificate** | Patient name, diagnosis, treatment, doctor name, hospital, dates |
| **Itemised Bill** | Line items with individual amounts and total |
| **Discharge Summary** | Diagnosis, treatment, admission date, discharge date |
| **Vehicle Damage Photo** | Damage location, damage description, severity (minor / moderate / severe) |
| **Vehicle Location Photo** | Location description, road conditions, weather conditions |

**Rules:**
- FR-04.1: Thai documents use Buddhist Era (พ.ศ.). AI MUST convert to Gregorian by subtracting 543. All stored dates: `YYYY-MM-DD`.
- FR-04.2: For damage and location photos, extract GPS coordinates from image EXIF if present.
- FR-04.3: Unreadable fields MUST be stored as `null` — never guessed.
- FR-04.4: Extracted data MUST be shown to the customer in the chat immediately after upload.

---

### FR-05: Driving License Ownership Confirmation (Car Damage — With Other Party Only)

| ID | Requirement |
|---|---|
| FR-05.1 | Ownership confirmation MUST only be triggered when the claim is **"With other party (มีคู่กรณี)"** |
| FR-05.2 | For a **no-other-party** claim, only the customer's driving license is requested — no ownership question is shown |
| FR-05.3 | For a **with-other-party** claim, every driving license upload MUST trigger an ownership question |
| FR-05.4 | The bot MUST present two quick-reply buttons: **"ของฉัน (ฝ่ายเรา)"** / **"คู่กรณี (อีกฝ่าย)"** |
| FR-05.5 | The same side (customer or other party) cannot be assigned twice |
| FR-05.6 | If a duplicate attempt is made, the bot MUST reject it with a clear explanation |

---

### FR-06: Data Storage per Claim

| ID | Requirement |
|---|---|
| FR-06.1 | Each claim MUST have its own dedicated folder on persistent storage, named by Claim ID |
| FR-06.2 | Every uploaded image MUST be saved as: `{document_category}_{YYYYMMDD_HHMMSS}.{ext}` |
| FR-06.3 | All AI-extracted data MUST be saved to `extracted_data.json` inside the claim folder |
| FR-06.4 | Claim metadata (status, memo, document list, response time metrics) MUST be saved to `status.yaml` |
| FR-06.5 | All stored data MUST survive container restarts via persistent volume |

```
Folder structure per claim:

{CLAIM_ID}/
  status.yaml             — status, memo, document list, metrics
  extracted_data.json     — all AI-extracted fields per document
  summary.md              — AI-generated claim summary
  documents/
    driving_license_20260226_120000.jpg
    vehicle_registration_20260226_120015.png
    vehicle_damage_photo_20260226_120030.jpg
```

---

### FR-07: Claim Submission

| ID | Requirement |
|---|---|
| FR-07.1 | The submit option MUST only appear when ALL required documents are uploaded |
| FR-07.2 | On submission attempt, the system re-validates completeness and rejects with a missing document list if incomplete |
| FR-07.3 | **Car Damage — With other party:** driving license (customer) + driving license (other party) + vehicle registration + ≥1 damage photo |
| FR-07.3b | **Car Damage — No other party:** driving license (customer) + vehicle registration + ≥1 damage photo |
| FR-07.4 | **Health:** citizen ID card + medical certificate + itemised bill + ≥1 receipt |
| FR-07.5 | On success, claim status MUST be set to "Submitted" and submission timestamp recorded |
| FR-07.6 | The bot MUST show the Claim ID to the customer after submission for tracking |

---

### FR-08: Eligibility Verdict (Car Damage)

| ID | Requirement |
|---|---|
| FR-08.1 | The bot MUST ask whether a counterpart vehicle was involved (quick-reply: "มีคู่กรณี" / "ไม่มีคู่กรณี") |
| FR-08.2 | After the damage photo is uploaded, the AI MUST produce an eligibility verdict by comparing the photo against the policy |
| FR-08.3 | Verdict = one of: 🟢 Eligible (recommended), 🟡 Eligible but cost below excess, 🔴 Not eligible |
| FR-08.4 | Every verdict MUST include: *"This is a preliminary AI assessment. Please confirm with your insurance company."* |

**Eligibility logic:**

| Insurance Class | No Counterpart | With Counterpart |
|:---:|:---:|:---:|
| ชั้น 1 | ✅ Eligible | ✅ Eligible |
| ชั้น 2+ / 2 | ❌ Not eligible | ✅ Eligible |
| ชั้น 3+ / 3 | ❌ Not eligible | ✅ Eligible |

---

### FR-09: Reviewer Web Dashboard

| ID | Requirement |
|---|---|
| FR-09.1 | Show all claims; searchable and filterable by status and claim type |
| FR-09.2 | Clicking a claim shows all uploaded document thumbnails |
| FR-09.3 | Clicking a thumbnail shows full-size image + AI-extracted data for that document |
| FR-09.4 | Reviewers can mark each document as **Useful** or **Not Useful** |
| FR-09.5 | Reviewers can update status: Submitted → Under Review → Pending → Approved → Rejected → Paid |
| FR-09.6 | Reviewers can add a free-text memo to any claim |
| FR-09.7 | All changes persist to `status.yaml` immediately |

---

### FR-10: Manager Web Dashboard

| ID | Requirement |
|---|---|
| FR-10.1 | Summary cards: Total claims, Average response time, Accuracy rate, Total paid (CD and H separately) |
| FR-10.2 | Daily bar chart showing claim counts split by type |
| FR-10.3 | Filter all data by date range and claim type |
| FR-10.4 | **Accuracy Rate** = Useful ÷ (Useful + Not Useful) × 100 |
| FR-10.5 | **Total Paid Amount** — only claims with status "Paid" |
| FR-10.6 | Clicking a row navigates to the Reviewer dashboard for that claim |

---

### FR-11: Admin Dashboard

| ID | Requirement |
|---|---|
| FR-11.1 | Search and filter application logs by level, category, and date |
| FR-11.2 | Change log verbosity at runtime without restarting the service |
| FR-11.3 | View AI token usage: total tokens, total cost, per-operation breakdown, usage over time |

---

### FR-12: General Bot Behaviour

| ID | Requirement |
|---|---|
| FR-12.1 | The bot MUST respond in **both Thai and English** in every message |
| FR-12.2 | All AI errors MUST produce user-friendly bilingual messages — no technical errors to customers |
| FR-12.3 | HTTP 429 rate-limit errors MUST trigger a polite retry prompt |
| FR-12.4 | If a user messages outside an active session, the bot MUST invite them to start a new claim |

---

## 9. Business Rules

### BR-01: Claim ID Sequence
- 6-digit, zero-padded (000001, 000042)
- CD and H have **independent counters**, both persisted across restarts in `sequence.json`

### BR-02: Buddhist Era → Gregorian Date Conversion
- Thai documents use Buddhist Era (พ.ศ.) — 543 years ahead of Gregorian
- **Conversion:** Gregorian year = พ.ศ. − 543
- All stored dates use: `YYYY-MM-DD`

### BR-03: Driving License — One Per Side (With-Other-Party Claims Only)
- Keys: `driving_license_customer` and `driving_license_other_party`
- `driving_license_other_party` is required **only** when the claim sub-type is **"With other party (มีคู่กรณี)"**
- For **"No other party"** claims, only `driving_license_customer` is collected — the bot MUST NOT ask for the counterpart's license
- A second upload for an already-assigned side MUST be rejected

### BR-04: Multiple Receipts (Health Claims)
- Multiple medical receipts allowed, stored in `medical_receipts[]` array
- No upper limit on receipt count

### BR-05: Unknown Documents Are Rejected
- "unknown" category = rejected; customer told which document types are accepted

### BR-06: Paid Amount Reporting
- Only claims with status **"Paid"** are counted in paid amount totals in Manager analytics

### BR-07: No Authentication (PoC)
- All web dashboard endpoints are publicly accessible in PoC scope
- Authentication required before production

---

## 10. Non-Functional Requirements

### Performance

| Requirement | Target |
|---|---|
| Text message reply | < 3 seconds |
| AI OCR for identity photo | < 10 seconds |
| Document categorisation | < 5 seconds per document |
| Data extraction per document | < 10 seconds per document |
| Damage analysis + eligibility verdict | < 30 seconds |
| Web dashboard page load | < 2 seconds |

### Storage

| Requirement | Description |
|---|---|
| Persistence | All claim data, sequences, logs, token records survive restarts |
| Claim structure | Per claim: `status.yaml`, `extracted_data.json`, `summary.md`, `documents/` |
| Log retention | 7-day retention, max 2,000 entries in memory |
| Token records | Last 10,000 AI API call records |

### Security

| Requirement | Description |
|---|---|
| Webhook verification | HMAC-SHA256 signature verification on all LINE webhook requests |
| Credentials | API keys in environment variables only — never in source code |
| PII in logs | National ID numbers and names MUST NOT appear in logs |
| AI file cleanup | Files uploaded to AI services deleted immediately after analysis |

### Reliability

| Requirement | Description |
|---|---|
| Graceful errors | All AI failures return user-friendly messages |
| Rate limit handling | HTTP 429 triggers a polite retry prompt |
| Auto-restart | `restart: unless-stopped` in Docker Compose |

---

## 11. System Integrations

| External System | Purpose | Method |
|---|---|---|
| **LINE Messaging API** | Receive user messages and images; send replies | REST API via `line-bot-sdk` Python v3 |
| **AI Vision (Gemini / GPT-4 Vision)** | Categorisation, OCR extraction, damage analysis, chat | AI SDK (Python) |
| **LINE Data API** | Download user-sent images | HTTP GET with Bearer token |
| **Policy Database** | Verify identity, retrieve coverage | PoC: JSON files. Production: DB or API |
| **Persistent File Storage** | Claim folders, images, JSON, logs | PoC: Docker volume. Production: Cloud storage (S3/GCS) |
| **ngrok** | Expose local bot to internet for webhook (PoC only) | Docker container |

---

## 12. Data Requirements

### 12.1 Policy Record — Car Damage

| Field | Example |
|---|---|
| id_card_number (13-digit) | 3100701443816 |
| name_th / name_en | สมชาย ใจดี / Somchai Jaidee |
| phone | 081-234-5678 |
| policy_number | CD-2026-001234 |
| vehicle_plate | กก 1234 กรุงเทพมหานคร |
| vehicle_brand / model / year / color | Toyota Camry 2.5 HV Premium, 2024, White Pearl |
| coverage_type | ชั้น 1 |
| coverage_amount (THB) | 1,000,000 |
| deductible (THB) | 5,000 |
| start_date / end_date | 2026-01-01 / 2026-12-31 |
| status | active |

### 12.2 Policy Record — Health

| Field | Example |
|---|---|
| id_card_number (13-digit) | 3100701443816 |
| name_th / name_en | สมชาย ใจดี |
| plan | Gold Health Plus |
| coverage_ipd (THB) | 500,000 |
| coverage_opd (THB) | 30,000 |
| room_per_night (THB) | 5,000 |
| start_date / end_date | 2026-01-01 / 2026-12-31 |
| status | active |

### 12.3 Extracted Data Storage Keys

**Car Damage:**

| Key | Stores |
|---|---|
| `driving_license_customer` | Name, license ID, citizen ID, dates |
| `driving_license_other_party` | Same for the counterpart driver — **present only when sub-type = "With other party"** |
| `vehicle_registration` | Plate, brand, chassis, engine, model year |
| `damage_photos[]` | Filename, description, severity, GPS (from EXIF) |
| `vehicle_location_photo` | Location, road/weather conditions, GPS |

**Health:**

| Key | Stores |
|---|---|
| `citizen_id_card` | Name, citizen ID, dates |
| `medical_certificate` | Patient, diagnosis, treatment, doctor, hospital, dates |
| `itemized_bill` | Line items with amounts, total |
| `discharge_summary` | Diagnosis, treatment, admission/discharge dates |
| `medical_receipts[]` | Hospital, billing number, total paid, date, itemised amounts |

### 12.4 Claim Status Lifecycle

```
Submitted → Under Review → Pending → Approved → Paid
                                   ↘
                                    Rejected
```

### 12.5 Document Accuracy Tagging (Reviewer)

| Tag | Meaning |
|---|---|
| `useful: true` | Document was clear and contributed to the claim decision |
| `useful: false` | Document was unclear or did not contribute |
| `useful: null` | Not yet reviewed |

---

## 13. Out of Scope

| # | Item | Note |
|---|---|---|
| 1 | Payment processing | Bot submits a claim; payment handled externally |
| 2 | Real-time policy database connection | PoC uses JSON files; DB integration future phase |
| 3 | Authentication for web dashboards | Required before production |
| 4 | Push notifications on status changes | Customer uses Claim ID to track; future feature |
| 5 | Non-car, non-health insurance types | Travel, life, property — out of scope |
| 6 | Languages beyond Thai + English | Two languages only |
| 7 | Mobile-responsive internal dashboards | Desktop browser only in PoC |
| 8 | Automated approval by AI | AI assists; human approves |
| 9 | Core insurance system integration | Future phase |
| 10 | Session persistence across restarts | In-memory only; restart clears sessions |

---

## 14. Assumptions & Constraints

### Assumptions

| # | Assumption |
|---|---|
| A1 | The policyholder has a valid LINE account |
| A2 | The customer's smartphone camera produces images clear enough for AI OCR |
| A3 | Policy JSON files are pre-loaded with correct records before go-live |
| A4 | Customers consent to photos and personal data being processed by a third-party AI service |
| A5 | The AI Vision model can reliably read standard Thai government documents |
| A6 | The company has an active LINE Official Account with Messaging API configured |

### Constraints

| # | Constraint |
|---|---|
| C1 | PoC runs on a single Docker host — no horizontal scaling |
| C2 | ngrok free tier URL changes on restart; LINE webhook must be re-registered manually |
| C3 | AI extraction time per document up to 10 seconds depending on image complexity |
| C4 | AI token usage incurs cost; all calls must be tracked and budgeted |
| C5 | LINE rate limits apply on messages per second |

---

## 15. Success Metrics (KPIs)

### Phase 1 — PoC (Months 1–3)

| KPI | Target |
|---|---|
| End-to-end submission success rate | ≥ 90% of sessions with valid policy + legible photos |
| AI document categorisation accuracy | ≥ 95% correct on first attempt |
| AI data extraction accuracy (name, ID, dates) | ≥ 90% correct values |
| Average time from trigger to submission | < 5 minutes |
| Bot recovery after error (cancel + restart) | 100% |

### Phase 2 — Production (Months 4–6)

| KPI | Target |
|---|---|
| Claims with all fields pre-extracted (no manual entry) | ≥ 70% |
| Reduction in intake errors vs. manual process | ≥ 30% fewer rejected / incomplete submissions |
| Reviewer time per claim (with dashboard) | ≥ 20% reduction vs. legacy |
| Customer satisfaction score | ≥ 4.0 / 5.0 stars |
| Monthly Active Users at 6 months | > 500 unique claimants |

---

## 16. Known Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | AI misreads a critical field (ID number, date), causing incorrect claim | Medium | High | Reviewer verifies all extracted data before approval |
| R2 | AI gives incorrect eligibility verdict, causing dispute | Medium | High | Mandatory disclaimer on every verdict; reviewer does independent check |
| R3 | Policy JSON file not pre-loaded with correct records before go-live | High | High | Data loading is a formal launch prerequisite |
| R4 | AI service downtime or rate limiting during peak hours | Low | High | Retry messages; session state preserved; customer can re-upload |
| R5 | Session data lost on container restart | High | Low | Acceptable PoC limitation; Redis TTL required for production |
| R6 | Customer uploads blurry, partial, or wrong document | High | Medium | AI rejects "unknown" with clear re-upload instructions |
| R7 | PII exposed in application logs | Medium | High | PII-free logging enforced; reviewed before production |
| R8 | AI token cost exceeds budget | Medium | Medium | Admin dashboard monitors cost; billing alerts; files deleted after use |
| R9 | Driving license assigned to wrong party | Medium | Medium | Explicit ownership confirmation; reviewer sees both licenses |
| R10 | ngrok tunnel breaks; LINE webhook stops | High | High | Document re-registration steps; production uses static domain |

---

## 17. Glossary

| Term | Definition |
|---|---|
| **LINE** | Thailand's most popular instant messaging app (50M+ users) |
| **LINE Messaging API** | Developer API for building automated LINE chatbots |
| **Flex Message** | Structured UI card format in LINE (rich media card) |
| **Quick Reply** | Tappable button options shown below a LINE message |
| **Webhook** | A URL LINE calls in real time to send user events to the bot |
| **Claim ID** | Unique claim identifier — e.g., CD-20260226-000001 |
| **OCR** | Optical Character Recognition — AI reading text from a photo |
| **AI Vision** | An AI model that understands images and extracts structured data |
| **Document Categorisation** | AI identifying the type of document in a photo |
| **Data Extraction** | AI reading and structuring specific fields from a document photo |
| **Session** | Temporary record tracking where a user is in the conversation flow |
| **Claim Type CD** | Car Damage (เคลมประกันรถยนต์) |
| **Claim Type H** | Health (เคลมประกันสุขภาพ) |
| **Policy (กรมธรรม์)** | The insurance contract defining coverage, exclusions, and deductible |
| **Excess / Deductible (ค่าเสียหายส่วนแรก)** | Amount policyholder pays before insurance covers the rest |
| **ชั้น 1 / 2+ / 3+** | Thai car insurance classes — Class 1 is most comprehensive |
| **Counterpart (คู่กรณี)** | The other vehicle and driver involved in the accident |
| **Buddhist Era (พ.ศ.)** | Thai calendar, 543 years ahead of Gregorian — used on Thai government documents |
| **EXIF** | Metadata embedded in photos; includes GPS coordinates on most smartphones |
| **GPS** | Location coordinates extracted from photo EXIF — records accident location |
| **Docker** | Containerisation platform used to package and run the application |
| **ngrok** | Tunnelling service creating a public HTTPS URL pointing to a local server |
| **PoC** | Proof of Concept — a prototype to validate the idea before full production investment |
| **Reviewer** | Claims staff who reviews documents and updates claim status |
| **Manager** | Operations manager who monitors overall performance via analytics |
| **Useful / Not Useful** | Reviewer tag on each document indicating contribution to the claim |
| **Accuracy Rate** | Useful ÷ (Useful + Not Useful) × 100 |
| **status.yaml** | Per-claim file: status, memo, document list, processing metrics |
| **extracted_data.json** | Per-claim file: all AI-extracted field values per document |
| **sequence.json** | System file persisting claim ID counters across restarts |

---

*For implementation details see [tech-spec.md](tech-spec.md) and [document-verify.md](document-verify.md). For the visual user journey see [user-journey.md](user-journey.md).*
