# Business Requirement Document (BRD)
## LINE Insurance Claim Eligibility Bot — "เช็คสิทธิ์เคลมด่วน"

**Document Version:** 1.0  
**Date:** February 2026  
**Status:** Draft  
**Owner:** Product Owner

---

## Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | February 2026 | Product Owner | Initial release |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Business Problem & Opportunity](#2-business-problem--opportunity)
3. [Project Objectives](#3-project-objectives)
4. [Stakeholders](#4-stakeholders)
5. [Target Users](#5-target-users)
6. [User Journey (Step-by-Step)](#6-user-journey-step-by-step)
7. [Functional Requirements](#7-functional-requirements)
8. [Business Rules](#8-business-rules)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [System Integrations](#10-system-integrations)
11. [Data Requirements](#11-data-requirements)
12. [Out of Scope](#12-out-of-scope)
13. [Assumptions & Constraints](#13-assumptions--constraints)
14. [Success Metrics (KPIs)](#14-success-metrics-kpis)
15. [Known Risks & Mitigations](#15-known-risks--mitigations)
16. [Glossary](#16-glossary)

---

## 1. Executive Summary

**Product Name:** เช็คสิทธิ์เคลมด่วน (Quick Insurance Claim Eligibility Check)  
**Platform:** LINE Messaging App (Chatbot)

This product is a **LINE chatbot** that helps car insurance policyholders instantly check whether they are eligible to file an insurance claim — directly from their LINE app, without calling a hotline or visiting a service center.

The user simply types a trigger phrase in LINE, provides their identity information, answers a few short questions, and sends a photo of the vehicle damage. The bot then uses **AI (Google Gemini)** to read the actual policy document and the damage photo, and delivers a clear eligibility verdict along with recommended next steps — all within one chat conversation.

---

## 2. Business Problem & Opportunity

### The Problem

When a vehicle accident happens, policyholders often face the following pain points:

| Pain Point | Description |
|---|---|
| **Long wait on hotlines** | Calling the insurance hotline can take 10–30+ minutes during peak hours |
| **Uncertainty about eligibility** | Customers are unsure whether their insurance type (Class 1, 2+, 3+) covers their specific incident |
| **Complexity of policy documents** | Policy PDFs are long and use legal or technical language that is hard for customers to understand |
| **Wasted trips** | Customers drive to service centers only to learn they are not eligible to claim |
| **Delayed action** | Not knowing the right steps quickly leads to missed evidence collection at the scene |

### The Opportunity

LINE is the most-used messaging app in Thailand, with over 50 million users. By placing this service inside LINE, the company can:

- Provide **instant self-service** to policyholders 24/7
- **Reduce inbound call volume** to the claims hotline
- **Improve customer satisfaction** by giving clear, fast answers
- **Increase digital touchpoints** with existing customers at no additional acquisition cost

---

## 3. Project Objectives

| # | Objective | Measurable Target |
|---|---|---|
| 1 | Enable policyholders to self-check claim eligibility without calling the hotline | Bot handles end-to-end in < 60 seconds |
| 2 | Reduce inbound claim-inquiry calls during business hours | 20% reduction in eligibility inquiry calls within 3 months of launch |
| 3 | Provide AI-powered damage assessment referencing the actual policy document | Accuracy confirmed by underwriting team spot-check: ≥ 90% correct verdict |
| 4 | Support multiple identity verification methods | Accept: ID card number, license plate, full name, or photo of either |
| 5 | Operate as a proof of concept (PoC) that can be scaled to production | PoC running on Docker with a clear production upgrade path documented |

---

## 4. Stakeholders

| Role | Name / Team | Responsibility |
|---|---|---|
| **Product Owner** | Insurance Digital Team | Defines requirements, accepts deliverables |
| **Business Sponsor** | Head of Claims Operations | Approves budget, defines success criteria |
| **End Users** | Thai car insurance policyholders | Use the bot on LINE |
| **Claims Operations Team** | Call center / adjusters | Receives escalations, validates AI accuracy |
| **IT / DevOps Team** | Technical Development Team | Builds, deploys, and maintains the system |
| **Compliance / Legal** | Risk & Compliance | Ensures AI output is properly disclaimed as advisory only |
| **LINE Platform** | LINE Corporation | Provides the messaging infrastructure and Messaging API |
| **Google (AI Provider)** | Google Cloud / AI Studio | Provides Gemini AI API for OCR and damage analysis |

---

## 5. Target Users

### Primary User

> A Thai car insurance policyholder who has just been involved in a vehicle accident (or potential damage event) and wants to know immediately whether they can file a claim.

**Profile:**
- Has an active LINE account (standard in Thailand)
- Owns a vehicle with an active insurance policy
- May not be familiar with insurance terminology
- Is under stress and wants a fast, clear answer
- Has a smartphone capable of taking photos

### Secondary User (Admin / Internal)

> Insurance operations staff who may monitor the bot dashboard, review AI verdicts for quality, or handle escalations from the bot.

---

## 6. User Journey (Step-by-Step)

The entire interaction happens inside LINE chat. Below is the full customer journey from trigger to result.

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER JOURNEY                         │
└─────────────────────────────────────────────────────────────┘

  STEP 1 — Trigger
  ─────────────────
  Customer types: "เช็คสิทธิ์เคลมด่วน"
  Bot responds with a welcome card asking for identity information.

  STEP 2 — Identity Verification
  ────────────────────────────────
  Customer provides ONE of the following:
    • 13-digit national ID number (typed)
    • Vehicle license plate number (typed)
    • Full name (typed)
    • Photo of ID card (AI reads it automatically)
    • Photo of license plate (AI reads it automatically)

  Bot searches its policy database and responds:
    • If 1 policy found → Shows policy details, moves to Step 3
    • If multiple policies found → Shows a vehicle selection carousel
    • If no policy found → Notifies customer and ends

  STEP 3 — Select Vehicle (if multiple policies)
  ────────────────────────────────────────────────
  Customer taps the correct vehicle from a carousel card.
  Bot confirms selection and moves to Step 4.

  STEP 4 — Counterpart Question
  ──────────────────────────────
  Bot asks: "Is there another vehicle involved in the accident?"
  Customer selects one of two quick-reply buttons:
    • ✅ Yes, there is a counterpart vehicle
    • ❌ No, it was a single-vehicle incident (hit a post, wall, etc.)

  STEP 5 — Incident Description (Optional)
  ──────────────────────────────────────────
  Bot presents a card asking for a brief description of what happened.
  Customer can:
    • Type a short description (e.g., "scraped a concrete pillar in a parking lot")
    • Tap "Skip" to proceed without a description

  STEP 6 — Damage Photo Submission
  ──────────────────────────────────
  Bot asks the customer to send a clear photo of the vehicle damage.
  Customer takes a photo and sends it in the chat.

  STEP 7 — AI Analysis (automated, ~10–30 seconds)
  ──────────────────────────────────────────────────
  Bot acknowledges the photo and begins analysis.
  In the background:
    1. Retrieves the customer's actual policy PDF from the database
    2. Sends both the damage photo and the policy PDF to Google Gemini AI
    3. AI reads the policy and evaluates the damage against policy conditions

  STEP 8 — Result Delivered
  ──────────────────────────
  Bot delivers a structured result card containing:
    ✦ Policy details (type, coverage, excess amount)
    ✦ Damage description (location, type, probable cause)
    ✦ Eligibility verdict (one of three outcomes — see Business Rules)
    ✦ Estimated repair cost range vs. excess
    ✦ 3 recommended next steps
    ✦ Call button to the insurance hotline (if number found in policy)
```

---

## 7. Functional Requirements

### FR-01: Trigger & Session Start

| ID | Requirement |
|---|---|
| FR-01.1 | The bot MUST start a new session when the user sends the exact phrase **"เช็คสิทธิ์เคลมด่วน"** |
| FR-01.2 | Sending the trigger phrase at any point MUST reset any existing session for that user |
| FR-01.3 | The bot MUST display a welcome UI card prompting the user to provide their identity information |

---

### FR-02: Identity Verification & Policy Lookup

| ID | Requirement |
|---|---|
| FR-02.1 | The bot MUST accept a **13-digit national ID number** (typed) and search for matching policies |
| FR-02.2 | The bot MUST accept a **vehicle license plate number** (typed) and search for matching policies |
| FR-02.3 | The bot MUST accept a **full or partial name** (typed) and search for matching policies |
| FR-02.4 | The bot MUST accept a **photo of a Thai national ID card** and automatically extract the ID number using AI OCR |
| FR-02.5 | The bot MUST accept a **photo of a vehicle license plate** and automatically extract the plate number using AI OCR |
| FR-02.6 | If exactly one policy is found, the bot MUST display the policy details and proceed |
| FR-02.7 | If more than one policy is found, the bot MUST display a vehicle selection carousel with one option per vehicle |
| FR-02.8 | If no policy is found, the bot MUST display a clear "not found" message and prompt the user to check their information |

---

### FR-03: Vehicle Selection

| ID | Requirement |
|---|---|
| FR-03.1 | When multiple policies are found, the bot MUST display a scrollable carousel with key vehicle information per card (plate, car model, policy type) |
| FR-03.2 | Each card MUST have a selectable button that sets the chosen vehicle and advances the conversation |

---

### FR-04: Counterpart Declaration

| ID | Requirement |
|---|---|
| FR-04.1 | After confirming the vehicle, the bot MUST ask whether there is a counterpart vehicle involved |
| FR-04.2 | The bot MUST present this question as **quick-reply buttons** ("มีคู่กรณี" / "ไม่มีคู่กรณี") so the user does not need to type |
| FR-04.3 | The user's answer MUST be stored and used as context in the AI analysis |

---

### FR-05: Optional Incident Description

| ID | Requirement |
|---|---|
| FR-05.1 | The bot MUST prompt the user to optionally describe the incident in their own words |
| FR-05.2 | The bot MUST provide a clearly visible **"Skip"** option (ข้าม) so the user is not blocked |
| FR-05.3 | If provided, the description MUST be passed as additional context to the AI analysis |

---

### FR-06: Damage Photo Submission

| ID | Requirement |
|---|---|
| FR-06.1 | The bot MUST accept a photo at the correct step in the conversation flow |
| FR-06.2 | If a photo is sent outside of the expected step, the bot MUST guide the user back to the correct step |
| FR-06.3 | The bot MUST display an acknowledgement message immediately after receiving the photo while AI analysis is in progress |

---

### FR-07: AI Damage Analysis

| ID | Requirement |
|---|---|
| FR-07.1 | The bot MUST retrieve the policyholder's actual **policy document (PDF)** and send it to the AI alongside the damage photo |
| FR-07.2 | If no policy PDF is available in the system, the bot MUST display a clear error message and NOT attempt partial analysis |
| FR-07.3 | The AI MUST produce a structured result that includes: policy details extracted from the PDF, damage description, eligibility verdict, repair cost estimate, and next steps |
| FR-07.4 | The AI result MUST be delivered to the user via a formatted card in LINE |
| FR-07.5 | If a hotline number is found within the AI result, the card MUST display a **tap-to-call button** |
| FR-07.6 | On any AI error, the bot MUST deliver a user-friendly error message in Thai and NOT expose technical error details |

---

### FR-08: Session Management

| ID | Requirement |
|---|---|
| FR-08.1 | Each user MUST have their own independent session that cannot interfere with other users |
| FR-08.2 | Session data MUST include: current step/state, selected policy details, counterpart answer, incident description |
| FR-08.3 | After the analysis result is delivered, the session MUST be marked as completed |
| FR-08.4 | From the "completed" state, the user can restart by sending the trigger phrase again |

---

### FR-09: General / Fallback Behaviour

| ID | Requirement |
|---|---|
| FR-09.1 | If a user sends a message that does not match any expected input at any step, the bot MUST respond with a helpful fallback message and remind the user to send the trigger phrase to start |
| FR-09.2 | All user-facing messages MUST be in Thai |

---

## 8. Business Rules

### BR-01: Claim Eligibility Logic by Insurance Class

This is the core business rule that the AI uses to determine eligibility.

| Insurance Class | Single Vehicle Incident (No Counterpart) | Two-Vehicle Incident (With Counterpart) |
|:---:|:---:|:---:|
| **ชั้น 1** (Class 1 — Comprehensive) | ✅ Eligible | ✅ Eligible |
| **ชั้น 2+** (Class 2+ — Semi-comprehensive) | ❌ Not eligible | ✅ Eligible |
| **ชั้น 2** (Class 2) | ❌ Not eligible | ✅ Eligible |
| **ชั้น 3+** (Class 3+ — Third-party+) | ❌ Not eligible | ✅ Eligible |
| **ชั้น 3** (Class 3 — Third-party) | ❌ Not eligible | ✅ Eligible |

> **Simple rule:** Class 1 covers single-vehicle incidents. All other classes require a counterpart (another vehicle involved).

---

### BR-02: Eligibility Verdict — Three Possible Outcomes

The AI MUST produce exactly one of three verdicts:

| Verdict | Colour | Condition |
|---|:---:|---|
| 🟢 **Eligible — Recommended to Claim** | Green | Policy covers the incident type AND estimated repair cost exceeds the policy excess amount |
| 🟡 **Eligible — With Own Expense** | Yellow | Policy covers the incident type BUT estimated repair cost is lower than or close to the excess amount (claiming may not be financially worthwhile) |
| 🔴 **Not Eligible** | Red | The policy class does NOT cover the incident type (e.g., Class 2+ with no counterpart) |

---

### BR-03: Disclaimer Requirement

Every AI analysis result MUST include the following advisory disclaimer:

> *"This is a preliminary AI assessment based on provided documents. Please confirm with your insurance company."*

The result is advisory only and does not constitute a formal claim decision.

---

### BR-04: Policy Document Required

- The AI analysis **cannot proceed** without a policy PDF on file.
- If the PDF is missing, the bot must refuse the analysis gracefully and direct the user to contact an agent.

---

### BR-05: Image Processing for Identity

- OCR (reading photos) applies to: Thai national ID cards and vehicle license plates only.
- If the AI cannot determine the document type or extract a value, the bot must ask the user to type the information manually.

---

## 9. Non-Functional Requirements

### Performance

| Requirement | Target |
|---|---|
| Bot response to text messages | < 3 seconds |
| OCR result for identity photos | < 10 seconds |
| AI damage analysis (end-to-end) | < 30 seconds |
| System uptime | 99% during business hours (8:00–22:00 weekdays) |

### Scalability

| Requirement | Target |
|---|---|
| Concurrent users supported (PoC) | At least 10 concurrent sessions |
| Concurrent users supported (Production) | Defined during production planning (Redis + horizontal scaling required) |

### Security

| Requirement | Description |
|---|---|
| Webhook verification | All LINE webhook requests MUST be verified using HMAC-SHA256 signature |
| Credentials management | All API keys and secrets MUST be stored in environment variables, never in source code |
| No PII in logs | Personal information (ID numbers, names) MUST NOT be printed in application logs |
| Policy document handling | Policy PDFs sent to Google Gemini MUST be deleted from Gemini storage immediately after analysis |

### Reliability

| Requirement | Description |
|---|---|
| Graceful error handling | All errors MUST produce user-friendly Thai messages; no technical stack traces shown to users |
| Self-healing deployment | Container MUST restart automatically on crash (`restart: always` in Docker Compose) |

### Usability

| Requirement | Description |
|---|---|
| Input flexibility | Users can identify themselves by 3 methods (ID, plate, name) plus 2 photo methods |
| Minimal typing | Quick-reply buttons MUST be used wherever the answer is a fixed choice |
| Thai language | All user-facing content MUST be in Thai |

---

## 10. System Integrations

| External System | Purpose | Integration Method |
|---|---|---|
| **LINE Messaging API** | Receive user messages; send replies and push messages to users | REST API via official `line-bot-sdk` (Python v3) |
| **Google Gemini AI** | OCR for ID/plate photos; multi-modal damage analysis with policy PDF | Google Generative AI Python SDK (`google-generativeai`) |
| **LINE Data API** | Download image files sent by users (damage photos, ID card photos) | Direct HTTP GET with Bearer token via `httpx` |
| **Policy Database** | Look up policyholder records and retrieve policy PDFs | **Currently:** In-memory mock data. **For Production:** To be replaced with a database (PostgreSQL / MySQL) or an internal policy management API — no changes to the rest of the system required. |
| **ngrok** | Expose the local bot server to the internet for LINE webhook delivery | Docker container running ngrok tunnel |

---

## 11. Data Requirements

### Policy Record — Minimum Required Fields

The system requires the following fields for each policy record. These fields are used during the conversation and the AI analysis.

| Field | Description | Example |
|---|---|---|
| Policy Number | Unique policy identifier | POL-2024-001234 |
| Title / First Name / Last Name | Policyholder full name | นาย สมชาย เข็มกลัด |
| National ID (CID) | 13-digit Thai national ID | 7564985348794 |
| License Plate | Vehicle registration | 1กข1234 |
| Car Model & Year | Vehicle make, model, year | Toyota Camry 2.5 Hybrid, 2023 |
| Insurance Type | Policy class | ชั้น 1, ชั้น 2+, ชั้น 3+ |
| Insurance Company | Insurer name | บริษัท กรุงเทพประกันภัย จำกัด (มหาชน) |
| Policy Start / End Date | Coverage period | 01/01/2024 – 31/12/2024 |
| Policy Status | Whether active or expired | active / expired |
| **Policy Document (PDF)** | **Full policy document in Base64 format — required for AI analysis** | Base64 string |

> **Important:** Without the policy PDF, the AI analysis cannot run. Policy documents should be loaded into the system before go-live.

### Data Storage — Current vs. Production

| Aspect | Current (PoC) | Production Requirement |
|---|---|---|
| Policy data | Hardcoded in `mock_data.py` | Relational database or policy API |
| Policy PDFs | Base64-encoded in memory | Object storage (S3 / GCS) referenced by URL |
| User sessions | In-memory Python dict | Redis with TTL expiry (e.g., 30 minutes of inactivity) |

---

## 12. Out of Scope

The following items are **explicitly outside the scope** of this version (v1.0):

| # | Out of Scope Item | Reason / Note |
|---|---|---|
| 1 | Actual claim submission | The bot only checks eligibility; it does not file a claim |
| 2 | Payment processing | No financial transactions are handled |
| 3 | Real-time policy database connection | PoC uses static mock data; production DB integration is a v2 item |
| 4 | Multi-language support (English / other) | Thai only in v1 |
| 5 | Support for non-vehicle insurance (health, life, etc.) | Car insurance only |
| 6 | Rich media output (video, sticker) | Text + Flex Message cards only |
| 7 | Admin dashboard or reporting UI | No management interface in v1 |
| 8 | proactive notifications (policy expiry reminders, etc.) | Reactive (user-initiated) only |
| 9 | Human agent handover within LINE | Out-of-scope; customer is given hotline number to call |
| 10 | Session data persistence across bot restarts | In-memory only; restart clears all sessions |

---

## 13. Assumptions & Constraints

### Assumptions

| # | Assumption |
|---|---|
| A1 | The policyholder's LINE account is registered under their own name/identity |
| A2 | Each policyholder has a valid LINE account on a smartphone capable of taking photos |
| A3 | Policy PDFs are available and loadable per customer record before production go-live |
| A4 | The insurance company has a LINE Official Account and a LINE Messaging API channel configured |
| A5 | Google Gemini 2.5 Flash API access is available and within budget for expected usage volume |
| A6 | Policyholders consent to their policy document and damage photos being processed by a third-party AI service (Google Gemini) |

### Constraints

| # | Constraint |
|---|---|
| C1 | The system runs on a single Docker host — no horizontal scaling in v1 |
| C2 | The ngrok tunnel URL changes on every restart when using the free tier — LINE webhook must be re-registered each time |
| C3 | Google Gemini AI response time is not guaranteed; analysis can take 10–30 seconds depending on PDF size |
| C4 | LINE Messaging API rate limits apply (maximum messages per user per second) |
| C5 | The free ngrok tier has connection limits; production must use a paid plan or a static public endpoint |

---

## 14. Success Metrics (KPIs)

### Phase 1 — PoC (Months 1–3)

| KPI | Target |
|---|---|
| Bot successfully completes end-to-end flow (from trigger to result) | ≥ 95% of sessions with a valid policy + PDF |
| AI eligibility verdict accuracy (underwriter spot-check sample) | ≥ 90% correct |
| Average time from trigger to result delivery | < 45 seconds |
| User able to restart after an error without contacting support | 100% (via trigger phrase reset) |

### Phase 2 — Production (Months 4–6)

| KPI | Target |
|---|---|
| Reduction in eligibility inquiry calls to the hotline | ≥ 20% decrease vs. baseline |
| Monthly Active Users (MAU) of the bot | > 500 unique policyholders |
| Customer satisfaction score (CSAT) via post-chat survey | ≥ 4.0 / 5.0 |
| Bot-handled sessions that require no human follow-up | ≥ 70% |

---

## 15. Known Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | AI gives incorrect eligibility verdict, leading to customer dispute | Medium | High | Add disclaimer on every result; run accuracy spot-checks; provide easy escalation to human agent |
| R2 | Policy PDF not loaded in system for a customer | High (PoC) | High | Require PDF loading as a pre-launch checklist item; bot must fail gracefully with clear "contact agent" message |
| R3 | Gemini AI API downtime or latency spike | Low | High | Bot must catch errors and ask user to retry; consider fallback to text-only analysis using policy metadata |
| R4 | Session data lost on container restart (in-memory storage) | High | Low | Acceptable for PoC; users can simply restart the flow; production must use Redis |
| R5 | ngrok URL changes after restart; LINE webhook breaks | High | Medium | Document re-registration steps; production should use a static domain |
| R6 | Unauthorised access or fake webhook requests | Low | High | All webhooks are verified using HMAC-SHA256 signature from LINE |
| R7 | PII (national ID, name) exposed in logs | Medium | High | Review logging configuration before production; avoid printing sensitive fields |
| R8 | AI processing cost exceeds budget due to high PDF upload volume | Medium | Medium | Monitor Gemini API usage and cost; set up billing alerts; delete uploaded files immediately after use (already implemented) |

---

## 16. Glossary

| Term | Definition |
|---|---|
| **LINE** | Thailand's most popular instant messaging and social platform, operated by LINE Corporation |
| **LINE Messaging API** | Developer API that allows businesses to build automated chatbots on LINE |
| **Flex Message** | A LINE message format that supports rich, structured UI cards (similar to rich cards) |
| **Quick Reply** | Tappable buttons that appear below a LINE message for fast selection |
| **Webhook** | A callback URL that LINE uses to forward user messages to the bot server in real time |
| **AI / Gemini** | Google Gemini 2.5 Flash — the AI model used for OCR and damage analysis |
| **OCR** | Optical Character Recognition — the process of reading text from an image |
| **Session** | A temporary record storing where a specific user is within the conversation flow |
| **State Machine** | The logic that tracks which step of the conversation each user is at and what input is valid next |
| **Policy (กรมธรรม์)** | The insurance contract document that defines coverage terms, exclusions, and excess amounts |
| **Excess (ค่าเสียหายส่วนแรก)** | The fixed amount the policyholder must pay out of pocket before the insurance company covers the rest |
| **ชั้น 1** | Class 1: Comprehensive car insurance — covers all types of damage regardless of counterpart involvement |
| **ชั้น 2+ / 3+** | Semi-comprehensive / limited coverage — only covers damages involving another vehicle as counterpart |
| **Counterpart (คู่กรณี)** | The other vehicle (and its driver) involved in a collision with the policyholder's vehicle |
| **Base64** | A text encoding of binary data (used here to store PDF files as text strings in the database) |
| **Docker** | A containerisation platform used to package and run the bot application |
| **ngrok** | A tunnelling service that creates a temporary public HTTPS URL pointing to a local server |
| **PoC** | Proof of Concept — a working prototype built to validate the core idea before full production investment |

---

*This document is intended for business and technical stakeholders. For implementation details, refer to [tech-spec.md](tech-spec.md).*
