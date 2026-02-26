"""
ai/analyse_damage.py — Eligibility verdict + damage analysis using Gemini.

Sends: damage photo image + policy PDF document.
Returns: Thai/English bilingual analysis result string.

Every response ends with the mandatory AI disclaimer (FR-08.4).
"""

import logging
import os
import tempfile
import time
from typing import Dict, Optional

import google.generativeai as genai
from PIL import Image
import io

from ai import call_gemini, get_model
from constants import GEMINI_MODEL

logger = logging.getLogger(__name__)

_DISCLAIMER = (
    "\n\n⚠️ *การประเมินนี้เป็นเพียงการประเมินเบื้องต้นโดย AI "
    "/ This is a preliminary AI assessment. "
    "Please confirm with your insurance company.*"
)

# Eligibility matrix — Class × counterpart
_ELIGIBILITY = {
    "ชั้น 1":  {"มีคู่กรณี": True,  "ไม่มีคู่กรณี": True},
    "ชั้น 2+": {"มีคู่กรณี": True,  "ไม่มีคู่กรณี": False},
    "ชั้น 2":  {"มีคู่กรณี": True,  "ไม่มีคู่กรณี": False},
    "ชั้น 3+": {"มีคู่กรณี": True,  "ไม่มีคู่กรณี": False},
    "ชั้น 3":  {"มีคู่กรณี": True,  "ไม่มีคู่กรณี": False},
}


def _build_prompt(policy_info: Dict, additional_info: Optional[str], has_counterpart: Optional[str]) -> str:
    first = policy_info.get("first_name", "").strip()
    last  = policy_info.get("last_name", "")
    plate = policy_info.get("vehicle_plate") or policy_info.get("plate", "")
    model = policy_info.get("vehicle_model") or policy_info.get("car_model", "")
    year  = policy_info.get("vehicle_year") or policy_info.get("car_year", "")
    coverage = policy_info.get("coverage_type") or policy_info.get("insurance_type", "")
    deductible = policy_info.get("deductible", "N/A")
    insurer = policy_info.get("insurance_company", "")

    counterpart_note = ""
    if has_counterpart == "มีคู่กรณี":
        counterpart_note = "Customer confirmed: WITH counterpart vehicle (มีคู่กรณี)."
    elif has_counterpart == "ไม่มีคู่กรณี":
        eligible = _ELIGIBILITY.get(coverage, {}).get("ไม่มีคู่กรณี", None)
        if eligible is False:
            counterpart_note = (
                f"Customer confirmed: NO counterpart (ไม่มีคู่กรณี). "
                f"Coverage class {coverage} does NOT cover single-vehicle incidents. "
                f"Verdict MUST be 🔴 Not eligible."
            )
        else:
            counterpart_note = "Customer confirmed: NO counterpart (ไม่มีคู่กรณี). Class 1 covers single-vehicle."

    additional_note = f'Customer description: "{additional_info}"' if additional_info else ""

    return f"""You are an expert Thai car insurance claims analyser for the "เช็คสิทธิ์เคลมด่วน" service.

Customer information:
- Name: {first} {last}
- Vehicle: {model} ({year}), plate {plate}
- Insurer: {insurer}
- Coverage class: {coverage}
- Deductible (Excess / ค่าเสียหายส่วนแรก): {deductible} THB

{counterpart_note}
{additional_note}

Analyse image 1 (damage photo) against image 2 (policy document PDF).

Reply in BOTH Thai AND English. Structure your reply exactly as follows:

สวัสดีครับ คุณ{first}: ผลการเช็คสิทธิ์เคลมด่วน / Quick Claim Eligibility Result for {first}

📄 ข้อมูลกรมธรรม์จากเอกสาร / Policy Details
• ประเภท / Class: [from document]
• ค่าเสียหายส่วนแรก / Deductible: [amount] บาท
• เบอร์แจ้งเหตุ / Claims hotline: [number from document]

🔍 วิเคราะห์ความเสียหาย / Damage Analysis
• ตำแหน่งที่เสียหาย / Damage location: [location]
• ลักษณะ / Description: [description]
• สาเหตุที่ประเมิน / Estimated cause: [cause]

⚖️ ผลการพิจารณา / Eligibility Verdict
[Show EXACTLY ONE of:]
🟢 ได้รับสิทธิ์เคลม (แนะนำ) / ELIGIBLE — Recommended
🟡 ได้รับสิทธิ์เคลม (ค่าซ่อมต่ำกว่า Excess) / ELIGIBLE — Repair cost below deductible
🔴 ไม่สามารถเคลมได้ / NOT ELIGIBLE — [reason referencing coverage class]

💰 ค่าใช้จ่ายเบื้องต้น / Estimated Costs
• ค่าซ่อมประเมิน / Estimated repair: [range] บาท
• ส่วนที่คุณจ่ายเอง / Your share (Excess): {deductible} บาท
• ประกันรับผิดชอบ / Insurer covers: [amount] บาท

📋 3 ขั้นตอนถัดไป / Next Steps
1. แจ้งเหตุทันที / Report immediately: โทร [hotline number]
2. นัดตรวจ / Schedule inspection
3. นำรถเข้าซ่อม / Proceed to repair
"""


def analyse_damage(
    image_bytes: bytes,
    policy_info: Dict,
    additional_info: Optional[str] = None,
    has_counterpart: Optional[str] = None,
) -> str:
    """Run damage analysis + eligibility verdict.

    Args:
        image_bytes:     Raw bytes of the damage photo.
        policy_info:     Policy record dict (from mock_data or DB).
        additional_info: Optional free-text incident description from customer.
        has_counterpart: "มีคู่กรณี" | "ไม่มีคู่กรณี" | None

    Returns:
        Bilingual analysis result string ending with AI disclaimer.
    """
    has_policy_doc = bool(policy_info.get("policy_document_base64"))
    if not has_policy_doc:
        logger.warning("No policy document found for analysis")
        return (
            "❌ ไม่พบเอกสารกรมธรรม์ / Policy document not found.\n"
            "กรุณาติดต่อเจ้าหน้าที่ / Please contact our staff."
            + _DISCLAIMER
        )

    import base64
    prompt = _build_prompt(policy_info, additional_info, has_counterpart)
    damage_img = Image.open(io.BytesIO(image_bytes))
    policy_pdf_bytes = base64.b64decode(policy_info["policy_document_base64"])

    uploaded = None
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(policy_pdf_bytes)
            tmp_path = tmp.name

        uploaded = genai.upload_file(tmp_path, mime_type="application/pdf")
        logger.info("Uploaded policy PDF to Gemini: %s", uploaded.name)
        time.sleep(2)  # allow Gemini to process the file

        model = get_model()
        response = model.generate_content([prompt, damage_img, uploaded])
        result = response.text

        # Record tokens manually since we bypass call_gemini()
        try:
            from ai import _append_token_record
            in_tok  = response.usage_metadata.prompt_token_count or 0
            out_tok = response.usage_metadata.candidates_token_count or 0
            _append_token_record("analyse_damage", in_tok, out_tok)
        except Exception:  # noqa: BLE001
            pass

        logger.info("Damage analysis complete")
        return result + _DISCLAIMER

    except Exception as exc:  # noqa: BLE001
        logger.error("Damage analysis error: %s", exc)
        return (
            f"❌ เกิดข้อผิดพลาดในการวิเคราะห์ / Analysis error: {exc}\n"
            "กรุณาลองใหม่อีกครั้ง / Please try again." + _DISCLAIMER
        )
    finally:
        if uploaded:
            try:
                genai.delete_file(uploaded.name)
                logger.debug("Deleted Gemini file %s", uploaded.name)
            except Exception:  # noqa: BLE001
                pass
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
