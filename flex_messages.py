"""
Flex Message Templates สำหรับ LINE Bot
ใช้สำหรับสร้าง UI ที่สวยงามบน LINE Chat
"""

from typing import Dict
from linebot.v3.messaging import FlexContainer


def create_request_info_flex() -> FlexContainer:
    """
    สร้าง Flex Message สำหรับขอข้อมูลชื่อและทะเบียนรถ

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🚗 ตรวจสอบสิทธิ์เคลม",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "กรุณาส่งรูปภาพหรือพิมพ์ข้อมูลดังนี้:",
                    "weight": "bold",
                    "size": "sm",
                    "margin": "md",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📸 ส่งรูปภาพ",
                            "size": "sm",
                            "weight": "bold",
                            "color": "#0066FF"
                        },
                        {
                            "type": "text",
                            "text": "• รูปบัตรประชาชน (อ่านเลขบัตรอัตโนมัติ)",
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs"
                        },
                        {
                            "type": "text",
                            "text": "• รูปทะเบียนรถ (อ่านเลขทะเบียนอัตโนมัติ)",
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs"
                        }
                    ],
                    "margin": "lg",
                    "backgroundColor": "#F0F7FF",
                    "paddingAll": "10px",
                    "cornerRadius": "md"
                },
                {
                    "type": "text",
                    "text": "⌨️ หรือพิมพ์ข้อมูล",
                    "weight": "bold",
                    "size": "sm",
                    "margin": "lg",
                    "color": "#0066FF"
                },
                {
                    "type": "text",
                    "text": "• เลขบัตรประชาชน 13 หลัก",
                    "size": "xs",
                    "color": "#666666",
                    "margin": "sm"
                },
                {
                    "type": "text",
                    "text": "• ทะเบียนรถ (เช่น 1กข1234)",
                    "size": "xs",
                    "color": "#666666",
                    "margin": "xs"
                },
                {
                    "type": "text",
                    "text": "• ชื่อและนามสกุล",
                    "size": "xs",
                    "color": "#666666",
                    "margin": "xs"
                }
            ],
            "spacing": "md",
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "❓ หากไม่ทราบทะเบียนรถ กรุณาติดต่อเจ้าหน้าที่",
                    "size": "xs",
                    "color": "#999999",
                    "wrap": True,
                    "margin": "md"
                }
            ],
            "paddingAll": "15px"
        }
    }

    return FlexContainer.from_dict(flex_message)

def create_vehicle_selection_flex(policies: list) -> FlexContainer:
    """
    สร้าง Flex Message สำหรับเลือกข้อมูลรถเมื่อพบหลายคัน
    """
    bubbles = []
    
    for i, policy in enumerate(policies):
        full_name = (f"{policy.get('first_name', '').strip()} {policy.get('last_name', '')}").strip() or "-"
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"🚗 คันที่ {i+1}",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#FFFFFF"
                    }
                ],
                "backgroundColor": "#0066FF",
                "paddingAll": "20px"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ทะเบียนรถ:",
                                "size": "sm",
                                "color": "#999999",
                                "flex": 4
                            },
                            {
                                "type": "text",
                                "text": policy["plate"],
                                "size": "sm",
                                "color": "#333333",
                                "weight": "bold",
                                "flex": 6
                            }
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {
                                "type": "text",
                                "text": "รุ่นรถ:",
                                "size": "sm",
                                "color": "#999999",
                                "flex": 4
                            },
                            {
                                "type": "text",
                                "text": policy.get("car_model", "-"),
                                "size": "sm",
                                "color": "#333333",
                                "flex": 6,
                                "wrap": True
                            }
                        ],
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ชื่อ-นามสกุล:",
                                "size": "sm",
                                "color": "#999999",
                                "flex": 4
                            },
                            {
                                "type": "text",
                                "text": full_name,
                                "size": "sm",
                                "color": "#333333",
                                "flex": 6,
                                "wrap": True
                            }
                        ],
                        "margin": "md"
                    }
                ],
                "flex": 1,
                "paddingAll": "20px"
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "message",
                            "label": "เลือกรถคันนี้",
                            "text": f"เลือกทะเบียน {policy['plate']}"
                        },
                        "style": "primary",
                        "color": "#0066FF"
                    }
                ],
                "paddingAll": "15px"
            }
        }
        bubbles.append(bubble)
        
    flex_message = {
        "type": "carousel",
        "contents": bubbles
    }
    
    return FlexContainer.from_dict(flex_message)

def create_policy_info_flex(policy_info: Dict) -> FlexContainer:
    """
    สร้าง Flex Message แสดงข้อมูลกรมธรรม์

    Args:
        policy_info: Dict ข้อมูลกรมธรรม์ที่มี keys:
            - policy_number: เลขกรมธรรม์
            - first_name: ชื่อ
            - last_name: นามสกุล
            - plate: ทะเบียนรถ
            - car_model: รุ่นรถ
            - car_year: ปีรถ
            - insurance_type: ประเภทประกัน

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    # รวมชื่อ-นามสกุล (ไม่รวมคำนำหน้า)
    full_name = (f"{policy_info.get('first_name', '').strip()} {policy_info.get('last_name', '')}").strip() or "-"

    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ พบข้อมูลกรมธรรม์",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": "เลขกรมธรรม์:",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0,
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": policy_info["policy_number"],
                            "size": "sm",
                            "color": "#333333",
                            "weight": "bold",
                            "wrap": True,
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ชื่อ-นามสกุล:",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": full_name,
                            "size": "sm",
                            "color": "#333333",
                            "wrap": True,
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ทะเบียนรถ:",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": policy_info.get("plate", "-"),
                            "size": "sm",
                            "color": "#333333",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": "รุ่นรถ:",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": f"{policy_info.get('car_model', '-')} ({policy_info.get('car_year', '-')})",
                            "size": "sm",
                            "color": "#333333",
                            "wrap": True,
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ประเภทประกัน:",
                            "size": "sm",
                            "color": "#999999",
                            "flex": 0
                        },
                        {
                            "type": "text",
                            "text": policy_info.get("insurance_type", "-"),
                            "size": "sm",
                            "color": "#0066FF",
                            "weight": "bold",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                }
            ],
            "spacing": "sm",
            "paddingAll": "20px"
        }
    }

    return FlexContainer.from_dict(flex_message)


def create_error_flex(error_message: str) -> FlexContainer:
    """
    สร้าง Flex Message สำหรับแสดง Error

    Args:
        error_message: ข้อความ error ที่ต้องการแสดง

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "❌ เกิดข้อผิดพลาด",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#FF0000",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": error_message,
                    "wrap": True,
                    "size": "md",
                    "color": "#333333"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "💡 กรุณาลองใหม่อีกครั้ง หรือติดต่อเจ้าหน้าที่",
                    "size": "xs",
                    "color": "#999999",
                    "wrap": True
                }
            ],
            "paddingAll": "15px"
        }
    }

    return FlexContainer.from_dict(flex_message)


def create_welcome_flex() -> FlexContainer:
    """
    สร้าง Flex Message สำหรับต้อนรับ

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "👋 สวัสดีค่ะ!",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                }
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "ยินดีต้อนรับสู่ระบบตรวจสอบสิทธิ์เคลมประกันรถยนต์",
                    "wrap": True,
                    "weight": "bold",
                    "size": "md",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "📋 บริการของเรา:",
                    "weight": "bold",
                    "size": "sm",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "• ตรวจสอบสิทธิ์การเคลมแบบเรียลไทม์\n• วิเคราะห์ความเสียหายด้วย AI\n• ประมาณการค่าใช้จ่าย\n• แนะนำขั้นตอนการเคลม",
                    "wrap": True,
                    "size": "xs",
                    "color": "#666666",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "กดปุ่มด้านล่างเพื่อเริ่มต้น",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "xl",
                    "align": "center"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "เช็คสิทธิ์เคลมด่วน",
                        "text": "เช็คสิทธิ์เคลมด่วน"
                    },
                    "style": "primary",
                    "color": "#0066FF"
                }
            ],
            "paddingAll": "15px"
        }
    }

    return FlexContainer.from_dict(flex_message)


def create_analysis_result_flex(
    summary_text: str,
    phone_number: str = None,
    insurance_company: str = "",
    claim_status: str = "unknown"
) -> FlexContainer:
    """
    สร้าง Flex Message แสดงผลการวิเคราะห์พร้อมปุ่มโทรออก

    Args:
        summary_text: ข้อความผลการวิเคราะห์จาก AI
        phone_number: เบอร์โทรแจ้งเหตุ (ไม่ต้องมี - หรือช่องว่าง)
        insurance_company: ชื่อบริษัทประกัน
        claim_status: สถานะการเคลม (approved/rejected/conditional/unknown)

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    # กำหนดสีปุ่มตามสถานะ
    button_colors = {
        "approved": "#17C964",      # เขียว - เคลมได้
        "rejected": "#F31260",      # แดง - เคลมไม่ได้
        "conditional": "#F5A524",   # ส้ม - เคลมได้แต่มีเงื่อนไข
        "unknown": "#0066FF"        # น้ำเงิน - ไม่ทราบสถานะ
    }

    button_color = button_colors.get(claim_status, "#0066FF")

    # สร้าง footer contents
    footer_contents = []

    # ถ้ามีเบอร์โทร → เพิ่มปุ่มโทรออก
    if phone_number:
        footer_contents.append({
            "type": "button",
            "style": "primary",
            "color": button_color,
            "height": "sm",
            "action": {
                "type": "uri",
                "label": f"📞 โทรแจ้งเหตุ {phone_number}",
                "uri": f"tel:{phone_number}"
            }
        })

    # เพิ่มปุ่ม "เช็ครถคันอื่น"
    footer_contents.append({
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "action": {
            "type": "message",
            "label": "🔄 เช็ครถคันอื่น",
            "text": "เช็คสิทธิ์เคลมด่วน"
        }
    })

    flex_message = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📋 ผลการวิเคราะห์",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#1E90FF",
                    "margin": "none"
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": summary_text,
                    "wrap": True,
                    "size": "sm",
                    "color": "#333333",
                    "margin": "md"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": footer_contents,
            "spacing": "sm",
            "paddingAll": "15px"
        }
    }

    return FlexContainer.from_dict(flex_message)


def create_input_method_flex() -> FlexContainer:
    """
    สร้าง Flex Message สำหรับให้ผู้ใช้เลือกวิธีการค้นหาข้อมูลกรมธรรม์

    วิธีที่รองรับ:
    1. ถ่ายรูปบัตรประชาชน (OCR)
    2. ถ่ายรูปป้ายทะเบียนรถ (OCR)
    3. พิมพ์ชื่อ-นามสกุล
    4. พิมพ์เลขทะเบียนรถ

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🔍 เลือกวิธีค้นหาข้อมูล",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                },
                {
                    "type": "text",
                    "text": "กรุณาเลือกวิธีที่สะดวกที่สุด",
                    "size": "sm",
                    "color": "#DDEEFF",
                    "margin": "sm"
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "📷 ถ่ายรูปบัตรประชาชน",
                        "text": "ใช้บัตรประชาชน"
                    },
                    "style": "primary",
                    "color": "#0066FF",
                    "margin": "md",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🚗 ถ่ายรูปป้ายทะเบียนรถ",
                        "text": "ใช้ป้ายทะเบียน"
                    },
                    "style": "primary",
                    "color": "#00A550",
                    "margin": "sm",
                    "height": "sm"
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "หรือพิมพ์ข้อมูลเอง:",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "xl",
                    "align": "center"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "✍️ พิมพ์ชื่อ-นามสกุล",
                        "text": "พิมพ์ชื่อ"
                    },
                    "style": "secondary",
                    "margin": "sm",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🔢 พิมพ์เลขทะเบียนรถ",
                        "text": "พิมพ์ทะเบียน"
                    },
                    "style": "secondary",
                    "margin": "sm",
                    "height": "sm"
                }
            ],
            "spacing": "sm",
            "paddingAll": "20px"
        }
    }

    return FlexContainer.from_dict(flex_message)


def create_vehicle_selection_flex(policies: list) -> FlexContainer:
    """
    สร้าง Flex Message แสดงรายการรถหลายคันให้ผู้ใช้เลือก
    """
    vehicle_buttons = []

    for i, policy in enumerate(policies):
        # เอาทะเบียนขึ้นก่อนตามความต้องการ
        car_label = f"{policy.get('plate', '-')} - {policy.get('car_model', '-')}"
        # ตัดข้อความให้ไม่เกิน 40 ตัวอักษร
        if len(car_label) > 40:
            car_label = car_label[:37] + "..."

        btn = {
            "type": "button",
            "action": {
                "type": "message",
                "label": car_label,
                "text": f"เลือกรถ:{policy['plate']}"
            },
            "style": "primary",
            "margin": "md",
            "height": "sm",
            "color": "#0066FF"
        }
        vehicle_buttons.append(btn)

    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🗂️ ผลการค้นหารถของคุณ",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF"
                },
                {
                    "type": "text",
                    "text": f"พบรถที่จดทะเบียนภายใต้ชื่อของคุณ {len(policies)} คัน",
                    "size": "xs",
                    "color": "#DDEEFF",
                    "margin": "xs"
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "กรุณาเลือกรถคันที่ต้องการแจ้งเคลม:",
                    "size": "sm",
                    "color": "#666666",
                    "margin": "none",
                    "weight": "bold"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": vehicle_buttons,
                    "margin": "md"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "💡 คลิกที่รถเพื่อดำเนินการต่อ",
                    "size": "xxs",
                    "color": "#999999",
                    "align": "center"
                }
            ],
            "paddingAll": "10px"
        }
    }

    return FlexContainer.from_dict(flex_message)



def create_additional_info_prompt_flex() -> FlexContainer:
    """
    สร้าง Flex Message สำหรับขอข้อมูลเพิ่มเติม (Optional)
    """
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📝 ข้อมูลเพิ่มเติม",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "15px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "ได้รับรูปภาพเรียบร้อยค่ะ! เพื่อความแม่นยำ คุณสามารถระบุรายละเอียดเหตุการณ์เพิ่มเติมได้นะคะ",
                    "size": "sm",
                    "color": "#333333",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ตัวอย่าง: ชนกำแพง, ประตูขวาเบียดเสา, ถอยชนกระถาง",
                            "size": "xs",
                            "color": "#666666",
                            "style": "italic",
                            "wrap": True
                        }
                    ],
                    "margin": "md",
                    "backgroundColor": "#F0F7FF",
                    "paddingAll": "10px",
                    "cornerRadius": "md"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "ข้ามและดูผลวิเคราะห์ ➡️",
                        "text": "ข้าม"
                    },
                    "style": "primary",
                    "color": "#00A550",
                    "height": "sm"
                },
                {
                    "type": "text",
                    "text": "หรือพิมพ์ข้อมูลแล้วส่งได้เลยค่ะ",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "md",
                    "align": "center"
                }
            ],
            "paddingAll": "15px"
        }
    }
    return FlexContainer.from_dict(flex_message)

def create_next_steps_flex() -> FlexContainer:
    """
    สร้าง Flex Message ถามขั้นตอนต่อไปหลังวิเคราะห์เสร็จ
    """
    flex_message = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🤔 ต้องการดำเนินการอย่างไรต่อดีคะ?",
                    "weight": "bold",
                    "size": "md",
                    "margin": "none"
                },
                {
                    "type": "text",
                    "text": "คุณสามารถเลือกดำเนินการต่อได้จากตัวเลือกด้านล่างนี้ค่ะ",
                    "size": "xs",
                    "color": "#666666",
                    "margin": "xs",
                    "wrap": True
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "📄 ส่งเคลมทันที",
                        "text": "ส่งเคลม"
                    },
                    "style": "primary",
                    "color": "#0066FF",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🚗 วิเคราะห์คันถัดไป",
                        "text": "เช็คสิทธิ์เคลมด่วน"
                    },
                    "style": "secondary",
                    "margin": "sm",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "👋 จบการสนทนา",
                        "text": "จบการสนทนา"
                    },
                    "margin": "sm",
                    "height": "sm"
                }
            ],
            "paddingAll": "15px"
        }
    }
    return FlexContainer.from_dict(flex_message)

def create_claim_submission_instructions_flex() -> FlexContainer:
    """
    สร้าง Flex Message แนะนำการส่งเอกสารเคลม
    """
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📝 ขั้นตอนการเตรียมส่งเคลม",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "md"
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "15px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "กรุณาเตรียมและส่งเอกสารดังต่อไปนี้ค่ะ (ส่งได้หลายไฟล์พร้อมกัน):",
                    "size": "sm",
                    "color": "#333333",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "1. 🪪 สำเนาใบขับขี่",
                            "size": "xs",
                            "margin": "sm",
                            "color": "#666666"
                        },
                        {
                            "type": "text",
                            "text": "2. 📄 สำเนาทะเบียนรถ",
                            "size": "xs",
                            "margin": "sm",
                            "color": "#666666"
                        },
                        {
                            "type": "text",
                            "text": "3. 📸 รูปความเสียหายมุมกว้าง (ให้เห็นทะเบียนรถ)",
                            "size": "xs",
                            "margin": "sm",
                            "color": "#666666"
                        },
                        {
                            "type": "text",
                            "text": "4. 📸 รูปคู่กรณี/ที่เกิดเหตุ (ถ้ามี)",
                            "size": "xs",
                            "margin": "sm",
                            "color": "#666666"
                        }
                    ],
                    "margin": "md",
                    "paddingStart": "10px"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "👇 คุณสามารถทยอยส่งรูปและเอกสารทั้งหมดมาได้เลยค่ะ AI กำลังรอรวบรวมข้อมูลให้คุณ...",
                    "size": "xxs",
                    "color": "#999999",
                    "align": "center",
                    "wrap": True
                }
            ],
            "paddingAll": "10px"
        }
    }
    return FlexContainer.from_dict(flex_message)


# ── Phase-2 additions (v2.0 handlers) ─────────────────────────────────────────

def create_claim_confirmed_flex(claim_id: str, claim_type: str) -> FlexContainer:
    """Confirmation bubble shown after a new claim is created."""
    type_label = "ประกันรถยนต์ / Car" if claim_type == "CD" else "สุขภาพ / Health"
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ สร้างเลขเคลมสำเร็จ",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                }
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "เลขเคลม:", "size": "sm", "color": "#999999", "flex": 4},
                        {"type": "text", "text": claim_id, "size": "sm", "color": "#333333", "weight": "bold", "flex": 6},
                    ],
                    "margin": "md",
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "ประเภท:", "size": "sm", "color": "#999999", "flex": 4},
                        {"type": "text", "text": type_label, "size": "sm", "color": "#333333", "flex": 6},
                    ],
                    "margin": "md",
                },
            ],
            "paddingAll": "20px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_claim_type_selector_flex() -> FlexContainer:
    """Quick-reply selector asking the user to choose CD or Health claim type."""
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "❓ กรุณาเลือกประเภทการเคลม",
                    "weight": "bold",
                    "size": "md",
                    "color": "#FFFFFF",
                }
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "Please select claim type:", "size": "sm", "color": "#666666"},
            ],
            "paddingAll": "20px",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "message", "label": "🚗 ประกันรถยนต์ (CD)", "text": "CD"},
                    "style": "primary",
                    "color": "#0066FF",
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "🏥 สุขภาพ (H)", "text": "H"},
                    "style": "secondary",
                    "margin": "sm",
                    "height": "sm",
                },
            ],
            "paddingAll": "15px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_health_policy_info_flex(policy_info: Dict) -> FlexContainer:
    """Policy card for a Health (H) claim."""
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "✅ พบข้อมูลกรมธรรม์สุขภาพ",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                }
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "เลขกรมธรรม์:", "size": "sm", "color": "#999999", "flex": 5},
                        {"type": "text", "text": policy_info.get("policy_number", "-"), "size": "sm", "color": "#333333", "weight": "bold", "flex": 7},
                    ],
                    "margin": "md",
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "แผน:", "size": "sm", "color": "#999999", "flex": 5},
                        {"type": "text", "text": policy_info.get("plan", "-"), "size": "sm", "color": "#0066FF", "weight": "bold", "flex": 7},
                    ],
                    "margin": "md",
                },
            ],
            "paddingAll": "20px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_document_checklist_flex(
    claim_type: str,
    has_counterpart,
    uploaded_docs: Dict,
) -> FlexContainer:
    """Document upload checklist showing required vs uploaded docs."""
    from constants import REQUIRED_DOCS
    reqs = REQUIRED_DOCS.get(claim_type, {})
    if claim_type == "CD":
        required_keys = reqs.get(has_counterpart, reqs.get("ไม่มีคู่กรณี", []))
    else:
        required_keys = reqs.get(None, [])

    label_map = {
        "driving_license_customer": "ใบขับขี่ (ของคุณ)",
        "driving_license_other_party": "ใบขับขี่ (คู่กรณี)",
        "vehicle_registration": "สมุดทะเบียนรถ",
        "vehicle_damage_photo": "รูปความเสียหาย",
        "citizen_id_card": "บัตรประชาชน",
        "medical_certificate": "ใบรับรองแพทย์",
        "itemised_bill": "ใบแจงค่าใช้จ่าย",
        "receipt": "ใบเสร็จรับเงิน",
    }

    rows = []
    for key in required_keys:
        done = key in uploaded_docs or any(u.startswith(key) for u in uploaded_docs)
        icon = "✅" if done else "⬜"
        rows.append({
            "type": "text",
            "text": f"{icon} {label_map.get(key, key)}",
            "size": "sm",
            "color": "#333333" if done else "#666666",
            "margin": "sm",
        })

    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "📋 รายการเอกสาร / Document Checklist", "weight": "bold", "size": "md", "color": "#FFFFFF"}
            ],
            "backgroundColor": "#0066FF",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": rows or [{"type": "text", "text": "ไม่มีเอกสารที่ต้องการ", "size": "sm", "color": "#999999"}],
            "paddingAll": "20px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_doc_received_flex(category: str, fields: Dict, missing: list) -> FlexContainer:
    """Confirmation bubble shown after a document image is accepted."""
    label_map = {
        "driving_license_customer": "ใบขับขี่ (ของคุณ)",
        "driving_license_other_party": "ใบขับขี่ (คู่กรณี)",
        "vehicle_registration": "สมุดทะเบียนรถ",
        "vehicle_damage_photo": "รูปความเสียหาย",
        "citizen_id_card": "บัตรประชาชน",
        "medical_certificate": "ใบรับรองแพทย์",
        "itemised_bill": "ใบแจงค่าใช้จ่าย",
        "receipt": "ใบเสร็จรับเงิน",
        "driving_license": "ใบขับขี่",
    }
    cat_label = label_map.get(category, category)
    remaining = len(missing)
    remaining_text = f"ยังขาดอีก {remaining} รายการ" if remaining else "ครบถ้วนแล้ว! 🎉"

    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"📄 รับเอกสาร: {cat_label}", "weight": "bold", "size": "sm", "color": "#FFFFFF"}
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "14px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": remaining_text, "size": "sm", "color": "#333333", "margin": "none"},
            ],
            "paddingAll": "18px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_submit_prompt_flex(claim_id: str, doc_count: int) -> FlexContainer:
    """Prompt bubble shown when all required documents are uploaded."""
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🎉 เอกสารครบแล้ว!", "weight": "bold", "size": "lg", "color": "#FFFFFF"}
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"อัปโหลดเอกสารแล้ว {doc_count} รายการ", "size": "sm", "color": "#333333"},
                {"type": "text", "text": f"เลขเคลม: {claim_id}", "size": "sm", "color": "#666666", "margin": "sm"},
            ],
            "paddingAll": "20px",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "message", "label": "📤 ส่งเคลม / Submit Claim", "text": "ส่งเคลม"},
                    "style": "primary",
                    "color": "#00B900",
                    "height": "sm",
                }
            ],
            "paddingAll": "15px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_ownership_question_flex(name: str) -> FlexContainer:
    """Ask which party owns a driving license that was just uploaded."""
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🪪 ใบขับขี่นี้เป็นของใคร?", "weight": "bold", "size": "md", "color": "#FFFFFF"}
            ],
            "backgroundColor": "#FF8C00",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"ชื่อในใบขับขี่: {name}", "size": "sm", "color": "#333333"},
            ],
            "paddingAll": "20px",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "message", "label": "ของฉัน (ฝ่ายเรา)", "text": "ของฉัน (ฝ่ายเรา)"},
                    "style": "primary",
                    "color": "#0066FF",
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {"type": "message", "label": "คู่กรณี (อีกฝ่าย)", "text": "คู่กรณี (อีกฝ่าย)"},
                    "style": "secondary",
                    "margin": "sm",
                    "height": "sm",
                },
            ],
            "paddingAll": "15px",
        },
    }
    return FlexContainer.from_dict(flex_message)


def create_submission_confirmed_flex(claim_id: str) -> FlexContainer:
    """Final confirmation bubble after a claim is successfully submitted."""
    flex_message = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "✅ ส่งเคลมสำเร็จ!", "weight": "bold", "size": "xl", "color": "#FFFFFF"}
            ],
            "backgroundColor": "#00B900",
            "paddingAll": "20px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "เราได้รับคำร้องของคุณแล้ว ทีมงานจะติดต่อกลับโดยเร็ว", "size": "sm", "color": "#333333", "wrap": True},
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {"type": "text", "text": "เลขเคลม:", "size": "sm", "color": "#999999", "flex": 4},
                        {"type": "text", "text": claim_id, "size": "sm", "color": "#0066FF", "weight": "bold", "flex": 8},
                    ],
                    "margin": "lg",
                },
            ],
            "paddingAll": "20px",
        },
    }
    return FlexContainer.from_dict(flex_message)
