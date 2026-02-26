import io
import json
import base64
import tempfile
import time
import re
import os
from typing import Dict, Optional, List
from PIL import Image

# Import LINE messaging components needed
from linebot.v3.messaging import (
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    FlexMessage
)

# Import Flex Messages
from flex_messages import (
    create_analysis_result_flex,
    create_next_steps_flex
)

def extract_phone_from_response(text: str) -> Optional[str]:
    """สกัดเบอร์โทรศัพท์จากข้อความตอบกลับของ AI"""
    patterns = [
        r'โทร\s*(\d{4})',                          # โทร 1557
        r'โทร\s*(\d{2,3}[-\s]?\d{3}[-\s]?\d{4})',  # โทร 02-123-4567
        r'เบอร์[:\s]*(\d{2,3}[-\s]?\d{3}[-\s]?\d{4})',  # เบอร์: 098-765-4321
        r'โทรศัพท์[:\s]*(\d{2,3}[-\s]?\d{3}[-\s]?\d{4})',  # โทรศัพท์: 02-123-4567
        r'แจ้งเหตุ[:\s]*(\d{4})',                 # แจ้งเหตุ 1557
        r'(?:โทร|เบอร์)\s*[:：]?\s*(\d{10})',     # โทร: 0987654321
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(1).replace('-', '').replace(' ', '')
            return phone
    return None

def extract_info_from_image_with_gemini(gemini_model, image_bytes: bytes) -> Dict:
    """ใช้ Gemini AI อ่านข้อมูลจากรูปภาพ (บัตรประชาชน หรือ ทะเบียนรถ)"""
    try:
        img = Image.open(io.BytesIO(image_bytes))

        prompt = """
        วิเคราะห์รูปภาพนี้ว่าเป็น "บัตรประชาชน" หรือ "ทะเบียนรถ" 
        แล้วสกัดข้อมูลที่สำคัญออกมาในรูปแบบ JSON ดังนี้:
        {
          "type": "id_card" หรือ "license_plate" หรือ "unknown",
          "value": "เลขบัตรประชาชน 13 หลัก" หรือ "เลขทะเบียนรถ (เช่น 1กข1234)" หรือ null
        }
        
        กฎ:
        1. ถ้าเป็นบัตรประชาชน ให้สกัดเลขบัตร 13 หลัก (เอาแค่ตัวเลข)
        2. ถ้าเป็นทะเบียนรถ ให้สกัดหมวดอักษรและตัวเลข (เช่น 1กข1234, ฌห55) ไม่ต้องเอาชื่อจังหวัด
        3. ถ้าไม่แน่ใจให้ตอบ unknown
        """

        response = gemini_model.generate_content([prompt, img])
        
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return {"type": "unknown", "value": None}

    except Exception as e:
        print(f"Error in extract_info_from_image_with_gemini: {str(e)}")
        return {"type": "unknown", "value": None}

def analyze_damage_with_gemini(
    gemini_model,
    genai,
    image_bytes: bytes,
    policy_info: Dict,
    additional_info: Optional[str] = None,
    has_counterpart: Optional[str] = None
) -> str:
    """ใช้ Gemini AI วิเคราะห์รูปภาพความเสียหายพร้อมเอกสารกรมธรรม์จริง"""
    try:
        has_policy_document = policy_info.get('policy_document_base64') is not None
        if not has_policy_document:
            return "❌ ไม่พบเอกสารกรมธรรม์\n\nกรุณาติดต่อเจ้าหน้าที่เพื่ออัพโหลดเอกสารกรมธรรม์ลงระบบก่อนใช้งาน"

        # Build System Prompt
        system_prompt = f"""
คุณคือ "AI ผู้เชี่ยวชาญด้านประกันรถยนต์และประเมินสินไหม" สำหรับบริการ "เช็คสิทธิ์เคลมด่วน"
วิเคราะห์ด้วยมาตรฐานระดับมืออาชีพ แม่นยำตามเงื่อนไขกรมธรรม์ และสื่อสารอย่างรวดเร็วเป็นกันเอง

**ภารกิจของคุณ:**
วิเคราะห์ภาพความเสียหาย (ภาพที่ 1) เปรียบเทียบกับเอกสารกรมธรรม์ (ภาพที่ 2/PDF) อย่างละเอียดและรวดเร็ว เพื่อให้คำแนะนำที่ถูกต้องที่สุดแก่ผู้เอาประกันภัย

**ข้อมูลพื้นฐานลูกค้า:**
- ผู้เอาประกัน: คุณ {policy_info['first_name'].strip()} {policy_info['last_name']}
- รถยนต์: {policy_info['car_model']} ({policy_info['car_year']}) ทะเบียน {policy_info['plate']}
- บริษัทประกัน: {policy_info['insurance_company']}"""

        if has_counterpart:
            if has_counterpart == "มีคู่กรณี":
                system_prompt += f"""
- สถานะคู่กรณี: ✅ **มีคู่กรณี** (ลูกค้ายืนยัน)

⚠️ **คำแนะนำสำหรับ AI:**
- ลูกค้ายืนยันว่า "มีคู่กรณี"
- ให้ตรวจสอบในรูปภาพว่ามีหลักฐานรถคู่กรณีหรือไม่
- ถ้าในรูปไม่เห็นคู่กรณีชัดเจน → แนะนำให้ลูกค้าถ่ายรูปคู่กรณีเพิ่ม
- ถ้ามีคู่กรณีจริง → ประกันชั้น 2+/2/3+/3 สามารถเคลมได้
- ชั้น 1 → เคลมได้ทุกกรณี (ไม่ว่าจะมีคู่กรณีหรือไม่)"""
            elif has_counterpart == "ไม่มีคู่กรณี":
                system_prompt += f"""
- สถานะคู่กรณี: ❌ **ไม่มีคู่กรณี** (ลูกค้ายืนยัน - ชนเสา/เฉี่ยวชนเอง)

⚠️ **คำแนะนำสำหรับ AI:**
- ลูกค้ายืนยันว่า "ไม่มีคู่กรณี" (ชนเสา, เฉี่ยวชนวัตถุ, ชนกำแพง)
- ตรวจสอบประเภทประกันจากเอกสาร:
  • ชั้น 1 → ✅ เคลมได้ (ไม่ต้องมีคู่กรณี)
  • ชั้น 2+/2/3+/3 → ❌ เคลมไม่ได้ (ต้องมีคู่กรณีเป็นยานพาหนะ)
- ถ้าเป็นชั้น 2+ → แจ้งชัดเจนว่า "ไม่มีสิทธิ์เคลม" พร้อมอ้างอิงเงื่อนไขจากเอกสาร"""

        if additional_info:
            system_prompt += f'\n- รายละเอียดจากลูกค้า: "{additional_info}"\n⚠️ **หมายเหตุ:** ใช้ข้อมูลนี้ประกอบการพิจารณา แต่ยึดรูปภาพและเอกสารกรมธรรม์เป็นหลัก'

        system_prompt += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**🎯 กฎการวิเคราะห์เชิงลึก (CRITICAL RULES):**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **CITATION (ต้องทำ):** ทุกครั้งที่ระบุเงื่อนไขประกัน ต้องใส่เลขบรรทัดหรือส่วนที่อ้างอิงจากเอกสาร เช่น [หน้า 1: ประเภทประกัน], [หน้า 1: ค่าเสียหายส่วนแรก]
2. **AI LOGIC:** - ถ้าเป็นชั้น 2+ หรือ 3+: ตรวจสอบอย่างเข้มงวดว่ารอยในภาพ "เป็นการชนกับยานพาหนะ" หรือไม่
   - การคำนวณ: เปรียบเทียบ "ค่าซ่อมประเมิน" vs "ค่า Excess" ในเอกสารจริงเสมอ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**📦 รูปแบบการตอบ (สำหรับ "เช็คสิทธิ์เคลมด่วน"):**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

สวัสดีครับ คุณ {policy_info['first_name'].strip()} สรุปผลการเช็คสิทธิ์เคลมด่วนดังนี้ครับ:

📄 **ข้อมูลกรมธรรม์จากเอกสาร**
• ประเภท: [ระบุ เช่น ประกันชั้น 2+] [หน้า 1]
• ค่าเสียหายส่วนแรก (Excess): [ระบุ] บาท [หน้า 1]
• เบอร์แจ้งเหตุ: [ระบุเบอร์ที่เจอในเอกสาร] [หน้า 1]

🔍 **วิเคราะห์ความเสียหายจากภาพ**
• พบรอยที่: [ระบุตำแหน่ง เช่น ประตูซ้าย]
• ลักษณะ: [เช่น รอยขูดลึกจากการเบียดวัตถุ]
• สาเหตุ: [เช่น เฉี่ยวชนไม่มีคู่กรณีเป็นยานพาหนะ]

⚖️ **ผลการพิจารณาสินไหม**
[เลือกแสดงผลเพียง 1 ข้อความ:]
• 🟢 **ได้รับสิทธิ์เคลม (แนะนำ)**
• 🟡 **ได้รับสิทธิ์เคลม (มีค่าใช้จ่าย)**
• 🔴 **ไม่สามารถเคลมได้**

• **เหตุผล:** [อธิบายสั้นๆ โดยอ้างอิงประเภทประกัน [หน้า 1] เทียบกับลักษณะรอยในภาพ]

💰 **สรุปค่าใช้จ่ายเบื้องต้น**
• ประเมินค่าซ่อม: [ช่วงราคา] บาท
• คุณจ่ายเอง (Excess): [ระบุ] บาท [หน้า 1]
• ประกันรับผิดชอบ: [ระบุ] บาท

📋 **3 ขั้นตอนดำเนินการด่วน**
1. **แจ้งเหตุทันที:** โทร [เบอร์จากเอกสาร]
2. **นัดตรวจสภาพ:** เตรียมใบขับขี่และภาพถ่ายนี้ไว้ให้เจ้าหน้าที่
3. **เข้าซ่อม:** นำรถเข้าอู่เครือ [ระบุชื่อบริษัทประกัน]

⚠️ **ข้อแนะนำเพิ่มเติม:** [เช่น แนะนำให้ซ่อมเองเพื่อรักษาประวัติลดเบี้ยปีหน้า]

*หมายเหตุ: เป็นการประเมินเบื้องต้นโดย AI โปรดตรวจสอบกับบริษัทประกันอีกครั้ง*
"""

        damage_image = Image.open(io.BytesIO(image_bytes))
        policy_doc_bytes = base64.b64decode(policy_info['policy_document_base64'])

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(policy_doc_bytes)
            temp_pdf_path = temp_pdf.name

        try:
            uploaded_pdf = genai.upload_file(temp_pdf_path, mime_type="application/pdf")
            time.sleep(2)
            response = gemini_model.generate_content([system_prompt, damage_image, uploaded_pdf])
            genai.delete_file(uploaded_pdf.name)
        finally:
            if os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)

        return response.text

    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        return f"❌ เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}"

def start_claim_analysis(
    line_bot_api, 
    gemini_model, 
    genai, 
    user_id, 
    image_bytes, 
    policy_info, 
    additional_info, 
    has_counterpart,
    user_sessions
):
    """ฟังก์ชันหลักคุม Flow การวิเคราะห์"""
    try:
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text="⏳ กำลังวิเคราะห์ข้อมูล...\n\nกรุณารอสักครู่ (ประมาณ 10-20 วินาที)")]
            )
        )

        analysis_result = analyze_damage_with_gemini(
            gemini_model,
            genai,
            image_bytes,
            policy_info,
            additional_info,
            has_counterpart
        )

        phone_number = extract_phone_from_response(analysis_result) or policy_info.get('phone')
        
        if phone_number:
            flex_message = create_analysis_result_flex(
                summary_text=analysis_result,
                phone_number=phone_number,
                insurance_company=policy_info.get('insurance_company', ''),
                claim_status="unknown"
            )
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[FlexMessage(alt_text="ผลการวิเคราะห์เคลมประกัน", contents=flex_message)]
                )
            )
        else:
            line_bot_api.push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[
                        TextMessage(text=analysis_result),
                        TextMessage(text='✅ การวิเคราะห์เสร็จสมบูรณ์')
                    ]
                )
            )

        # ส่งคำถามขั้นตอนต่อไปต่อเลย
        next_steps_flex = create_next_steps_flex()
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[FlexMessage(alt_text="คุณต้องการดำเนินการอย่างไรต่อ?", contents=next_steps_flex)]
            )
        )

        user_sessions[user_id]["state"] = "completed"

    except Exception as e:
        print(f"❌ Error in start_claim_analysis: {str(e)}")
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=f"❌ เกิดข้อผิดพลาด: {str(e)}")]
            )
        )
