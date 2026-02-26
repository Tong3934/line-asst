# LINE Insurance Claim Bot - System Specification (Detailed Version)

เอกสารฉบับนี้เป็นข้อกำหนดระบบ (System Specification) แบบละเอียด สำหรับนักพัฒนาในทีมหรือ AI Developer เพื่อทำความเข้าใจสถาปัตยกรรม (Architecture) ของโปรเจกต์ โฟลว์การทำงาน (Workflow/State Machine) และโครงสร้างโค้ดโดยละเอียด

---

## 1. Project Overview & Architecture
ระบบ LINE Bot สำหรับบริการ "เช็คสิทธิ์เคลมด่วน" ช่วยให้ลูกค้าประเมินความเสียหายและเช็คสิทธิ์การเคลมประกันรถยนต์เบื้องต้นผ่าน AI (Google Gemini) โดยมีสถาปัตยกรรมหลักดังนี้:

*   **API Framework:** FastAPI (Python) ทำหน้าที่เป็น Webhook Server รับ Event จาก LINE
*   **Messaging API:** `line-bot-sdk` (v3) ใช้สำหรับรับ Message Event และส่งข้อความตอบกลับ (Reply/Push) รวมถึง Flex Message ที่เป็น UI หลัก
*   **AI Engine:** `google-generativeai` (Gemini 2.5 Flash) ทำหน้าที่สองส่วน:
    1.  **OCR/Information Extraction:** อ่านข้อมูลจากภาพบัตรประชาชนและป้ายทะเบียน
    2.  **Multimodal Claim Analysis:** วิเคราะห์ภาพรอยความเสียหาย ร่วมกับเอกสารกรมธรรม์ (PDF) และข้อมูลลูกค้า เพื่อตัดสินสิทธิ์การเคลมตามเงื่อนไข
*   **State Management:** In-memory Dictionary เก็บสถานะ (State) ของผู้ใช้แต่ละคน เพื่อควบคุมบทสนทนาแบบ State Machine

---

## 2. Directory & Module Structure

*   **`config.py`**: จัดการ Environment Variables (`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`, `GEMINI_API_KEY`) และสร้าง Instance ของ LINE API (`configuration`, `handler`) รวมถึง Gemini Model
*   **`main.py`**: Entry Point ของระบบ มีการตั้งค่า FastAPI Router (`/webhook`, `/health`) และ Webhook Event Handlers (`handle_text_message`, `handle_image_message`) ทำหน้าที่เป็นตัว Route State ต่างๆ
*   **`session_manager.py`**: จัดการข้อมูลผู้ใช้ที่กำลังคุยอยู่ (Session Context)
    *   `get_session(user_id)` / `set_state(...)` / `reset_session(...)`
    *   `process_search_result(...)`: ฟังก์ชันแยกสำหรับจัดการตรรกะเมื่อค้นหากรมธรรม์เจอ (1 คัน, คัน, หรือไม่เจอเลย)
*   **`claim_engine.py`**: โค้ดส่วนที่คุยกับระบบ AI
    *   `extract_info_from_image_with_gemini`: ทำ OCR
    *   `analyze_damage_with_gemini`: สร้าง Prompt วิเคราะห์ความเสียหาย อัปโหลด PDF เข้า Gemini และสั่ง Generate Content
    *   `start_claim_analysis`: Wrapper คุม Flow การเรียก AI และส่ง Flex Message กลับไปที่ผู้ใช้
*   **`flex_messages.py`**: แหล่งรวม UI Layout แบบ Flex Message
    *   `create_input_method_flex`, `create_vehicle_selection_flex`, `create_policy_info_flex`, `create_analysis_result_flex`, `create_next_steps_flex`, `create_claim_submission_instructions_flex` ฯลฯ
*   **`mock_data.py`**: ฐานข้อมูลจำลอง (เสมือน DB จริง) จัดเก็บข้อมูลลูกค้าแบบ JSON พร้อมฟังก์ชันค้นหา (`search_policies_by_cid`, `_plate`, `_phone`, `_name`) ทุกกรมธรรม์จะมี Base64 ของ PDF แนบมาด้วย

---

## 3. Conversation Flow & State Machine (Detailed)

ระบบทำงานบนแนวคิด Finite State Machine (FSM) โดยยึด Current State จาก `session_manager.py` เป็นหลัก

### 3.1 การเริ่มต้น (Start)
*   **State:** `None` หรือ `idle` หรือ `completed`
*   **Trigger:** ผู้ใช้ส่งข้อความ "เช็คสิทธิ์เคลมด่วน" (หรือจาก Rich Menu)
*   **Action:** ระบบเปลี่ยน State เป็น `waiting_for_info` และส่ง `create_input_method_flex()` ให้ลูกค้าเลือกว่าจะป้อนข้อมูลแบบไหน (บัตร ปชช., ทะเบียน, พิมพ์ชื่อ)

### 3.2 การค้นหากรมธรรม์ (Finding Policy)
*   **State:** `waiting_for_info`
*   **Trigger (Text):**
    *   ถ้าผู้ใช้กดปุ่ม Flex: ส่งคำแนะนำเพิ่มเติม (เช่น "กรุณาส่งรูปบัตรประชาชน")
    *   ถ้าผู้ใช้พิมพ์ข้อมูล: โค้ดใน `main.py` จะใช้ Regex เช็คว่าเป็นเลข 13 หลัก (CID), เลขโทรศัพท์ 9-10 หลัก (Phone), หรือข้อความทั่วไป (Plate/Name) แล้วเรียก `mock_data.py`
*   **Trigger (Image):**
    *   ผู้ใช้ส่งรูป: `handle_image_message` จะดึง byte รูป ส่งเข้า `claim_engine.extract_info_from_image_with_gemini` เพื่อสกัดประเภท (Type) และค่า (Value) ออกมาค้นหา
*   **Post-Search Logic (`process_search_result`):**
    *   **ไม่เจอ:** แจ้งเตือนข้อผิดพลาด และอยู่ใน State `waiting_for_info` เหมือนเดิม
    *   **เจอ > 1 คัน:** เปลี่ยน State เป็น `waiting_for_vehicle_selection` ส่ง Flex Message โชว์รถทุกคันแบบ Carousel
    *   **เจอ 1 คัน:** เปลี่ยน State เป็น `waiting_for_counterpart` แสดงข้อมูลกรมธรรม์และถามว่า "มีคู่กรณีหรือไม่?" (Quick Reply)

### 3.3 การเลือกรถ (Vehicle Selection)
*   **State:** `waiting_for_vehicle_selection`
*   **Trigger:** ผู้ใช้กดยืนยันเลือกรถจาก Carousel (ข้อความขึ้นต้นด้วย "เลือกรถ:")
*   **Action:** ระบุคันรถที่เลือก เปลี่ยน State เป็น `waiting_for_counterpart` และถามเรื่องคู่กรณี

### 3.4 ระบุสถานะคู่กรณี (Counterpart Info)
*   **State:** `waiting_for_counterpart`
*   **Trigger:** ผู้ใช้เลือก "มีคู่กรณี" หรือ "ไม่มีคู่กรณี"
*   **Action:** เก็บค่า `has_counterpart` เปลี่ยน State เป็น `waiting_for_image` และสั่งให้ผู้ใช้ถ่ายรูปความเสียหาย

### 3.5 รับภาพความเสียหาย (Damage Image Gathering)
*   **State:** `waiting_for_image`
*   **Trigger:** ผู้ใช้ส่งรูป
*   **Action:** โหลดรูประบบ `image_bytes` เก็บไว้ชั่วคราว เปลี่ยน State เป็น `waiting_for_additional_info` และถามเพิ่มเติมว่าต้องการอธิบายลักษณะการชนเพิ่มเติมหรือไม่ (มีปุ่ม "ข้าม")

### 3.6 การวิเคราะห์ระบบและสรุปผล (AI Analysis)
*   **State:** `waiting_for_additional_info`
*   **Trigger:** ผู้ใช้อธิบายรายละเอียดเพิ่มเติม หรือกด "ข้าม"
*   **Action:**
    1.  รวม Context ทั้งหมด: ภาพรอยชน, ไฟล์ Policy Document (แปลง Base64 กลับเป็น Byte และเขียนลง Temp File .pdf เพื่ออัปโหลดเข้า Gemini), สถานะคู่กรณี, และคำอธิบายเพิ่มเติม
    2.  ส่งไปยัง `analyze_damage_with_gemini` โดยถูกพ่วงด้วย System Prompt อย่างเข้มงวดให้ AI ประเมินเงื่อนไขชั้นประกัน (ชั้น 1, 2+, 3 ฯลฯ)
    3.  เมื่อ AI ตอบกลับ จะส่ง `create_analysis_result_flex` พร้อมผลลัพธ์
    4.  ส่ง `create_next_steps_flex` ถามว่าจะทำอะไรต่อ (ส่งเคลม / วิเคราะห์คันอื่น / จบ)
    5.  เปลี่ยน State เป็น `completed`

### 3.7 ขั้นตอนการส่งเคลมต่อเนื่อง (Claim Submission Setup)
*   **State:** `completed`
*   **Trigger:** ผู้ใช้เลือก "ส่งเคลม"
*   **Action:** เปลี่ยน State เป็น `waiting_for_claim_documents` ส่ง `create_claim_submission_instructions_flex` แจ้งรายการเอกสารที่จำเป็น (ใบขับขี่, ทะเบียนรถ, ภาพมุมกว้าง ฯลฯ)

### 3.8 การรวบรวมเอกสารเคลม (Document Gathering)
*   **State:** `waiting_for_claim_documents`
*   **Trigger (Image):** ผู้ใช้ทยอยส่งรูป โค้ดจะตอบรับ "ได้รับเอกสารแล้ว... ส่งเพิ่มต่อได้" (ในอนาคตควรต่อ API ยิงเข้าชหลังบ้านทีละรูป)
*   **Trigger (Text "เสร็จสิ้น"):** ผู้ใช้ส่งครบแล้ว โค้ดสรุปการทำงาน "เจ้าหน้าที่จะดำเนินการต่อ" และ Reset State กลับไปเตรียมเริ่มต้นใหม่

---

## 4. Prompt Engineering Context

จุดสำคัญที่จะส่งผลต่อความแม่นยำของ AI อยู่ที่ `claim_engine.py -> analyze_damage_with_gemini`
*   **PDF Analysis:** รหัสจะแปลงไฟล์กรมธรรม์ของ mock data เป็น `.pdf` ส่งเข้า `genai.upload_file` ให้ AI อ่านเงื่อนไขตัวจริง (RAG แบบ On-the-fly)
*   **Logic Injection:** โค้ดจะเอา `has_counterpart` ผสมเข้าไปใน Prompt โดยตรง เพื่อบังคับ AI ว่า ถ้าเป็น "ไม่มีคู่กรณี" และเอกสารบอกว่าเป็นชั้น 2+ AI บังคับต้องสรุปว่า "เคลมไม่ได้" ตรรกะนี้จะปิดช่องโหว่การวิเคราะห์ผิดจากทางฝั่ง AI ได้ดี

---

## 5. Development Setup & Deployment

1.  **Dependencies:**
    *   `fastapi`, `uvicorn`, `line-bot-sdk`, `google-generativeai`, `python-dotenv`, `httpx`, `pillow`
2.  **Environment Variables:**
    *   สร้างไฟล์ `.env` ประกอบด้วย:
        *   `LINE_CHANNEL_ACCESS_TOKEN`
        *   `LINE_CHANNEL_SECRET`
        *   `GEMINI_API_KEY`
3.  **Running Locally:**
    *   `python main.py` (หรือใช้ `uvicorn main:app --reload --port 8000`)
    *   ทดสอบ LINE Webhook จาก Local ใช้ Ngrok: `ngrok http 8000` นำ URL SSL + `/webhook` ไปใส่ใน LINE Deveeopers Console

---

## 6. แนวทางพัฒนาต่อ (Next Steps for AI/Team)

หากทีมหรือ AI ตัวใหม่ต้องรับช่วงต่อ ขอแนะนำสิ่งที่ควร Focus คือ:

1.  **Scale Database (Priority 1):** ถอด `mock_data.py` ออก แล้วต่อ DB (PostgreSQL, MongoDB) พร้อมจัดเก็บ File กรมธรรม์ขึ้น Cloud Storage (S3, GCS) คืนค่าเป็น URL รูปแบบ Signed-URL แล้วโหลดให้ Gemini
2.  **Refactoring Controllers (Priority 2):** เมื่อ Flow ซับซ้อนขึ้น ควรแตก `main.py` ทำ Controller สำหรับแต่ละ State แยกออกจากกัน (เช่น `state_handlers/waiting_for_info_handler.py`)
3.  **Redis for Scale (Priority 2):** เปลี่ยนไปใช้ Redis เพื่อแบ็คอัป Session หาก Service Restart ข้อมูลจะได้ไม่หาย และรองรับ Multi-instance Deploy
4.  **Claim System Integration (Priority 1):** เพิ่มลอจิกใน State `waiting_for_claim_documents` ให้แพ็คข้อมูลทั้งหมดแล้วเรียก API ไปยังระบบ Core Insurance หรือระบบ CRM แจ้งเตือนเจ้าหน้าที่พิจารณาสินไหม
5.  **Multi-image Damage (Priority 3):** อัปเกรดให้วิเคราะห์รูปภาพรอยชนแบบ หลายรูปพร้อมกัน โดยให้ Bot สะสมภาพครบแล้วค่อยกดให้ AI วิจารณ์

---
*(End of System Specification)*
