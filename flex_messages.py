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
        full_name = f"{policy['first_name'].strip()} {policy['last_name']}"
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
    full_name = f"{policy_info['first_name'].strip()} {policy_info['last_name']}"

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
                            "text": policy_info["plate"],
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
                            "text": f"{policy_info['car_model']} ({policy_info['car_year']})",
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
                            "text": policy_info["insurance_type"],
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
    (ใช้เมื่อค้นหาด้วยชื่อหรือบัตรประชาชนแล้วพบหลายกรมธรรม์)

    Args:
        policies: List ของ Dict ข้อมูลกรมธรรม์ที่พบ

    Returns:
        FlexContainer: Flex Message พร้อมส่งผ่าน LINE API
    """
    vehicle_buttons = []

    for i, policy in enumerate(policies):
        car_label = f"{policy['car_model']} - {policy['plate']}"
        # ตัดข้อความให้ไม่เกิน 40 ตัวอักษร (LINE label limit)
        if len(car_label) > 40:
            car_label = car_label[:37] + "..."

        btn = {
            "type": "button",
            "action": {
                "type": "message",
                "label": car_label,
                "text": f"เลือกรถ:{policy['plate']}"
            },
            "style": "primary" if i == 0 else "secondary",
            "margin": "sm",
            "height": "sm"
        }
        if i == 0:
            btn["color"] = "#0066FF"

        vehicle_buttons.append(btn)

    flex_message = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🚗 พบรถหลายคัน",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#FFFFFF"
                },
                {
                    "type": "text",
                    "text": f"พบ {len(policies)} รายการ กรุณาเลือกรถของท่าน",
                    "size": "sm",
                    "color": "#DDEEFF",
                    "margin": "sm"
                }
            ],
            "backgroundColor": "#FF6B00",
            "paddingAll": "20px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": vehicle_buttons,
            "spacing": "sm",
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "💡 กดเลือกรถที่ต้องการเคลมประกัน",
                    "size": "xs",
                    "color": "#999999",
                    "wrap": True,
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
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "📝 รายละเอียดเพิ่มเติม (Optional)",
                    "weight": "bold",
                    "size": "md",
                    "color": "#0066FF"
                },
                {
                    "type": "text",
                    "text": "กรุณาพิมพ์รายละเอียดเหตุการณ์เบื้องต้น\nเช่น: ชนท้าย, ประตูบุบ, กระจกแตก",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True,
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "หรือพิมพ์ 'ข้าม' หากไม่ต้องการระบุ",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "md",
                    "style": "italic"
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
                        "label": "ข้าม",
                        "text": "ข้าม"
                    },
                    "style": "secondary",
                    "height": "sm"
                }
            ],
            "paddingAll": "10px"
        }
    }
    return FlexContainer.from_dict(flex_message)

