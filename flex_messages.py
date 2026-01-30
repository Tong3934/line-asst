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
                    "text": "กรุณาส่งข้อมูลในรูปแบบ:",
                    "weight": "bold",
                    "size": "md",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "ชื่อ-นามสกุล, ทะเบียนรถ, รายละเอียด",
                    "size": "sm",
                    "color": "#0066FF",
                    "margin": "md",
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": "(รายละเอียดใส่หรือไม่ใส่ก็ได้)",
                    "size": "xxs",
                    "color": "#999999",
                    "margin": "xs"
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "ตัวอย่าง:",
                    "size": "sm",
                    "color": "#999999",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "• สมชาย เข็มกลัด, 1กข1234",
                    "size": "sm",
                    "color": "#666666",
                    "margin": "sm",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "• สมชาย เข็มกลัด, 1กข1234, ชนเสาหน้า",
                    "size": "sm",
                    "color": "#666666",
                    "margin": "xs",
                    "wrap": True
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
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💡 รายละเอียดเพิ่มเติม (optional):",
                            "size": "xs",
                            "color": "#0066FF",
                            "weight": "bold",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "เช่น: ชนท้าย, ประตูบุบ, กระจกแตก",
                            "size": "xs",
                            "color": "#666666",
                            "margin": "xs",
                            "wrap": True
                        }
                    ],
                    "backgroundColor": "#F0F7FF",
                    "cornerRadius": "md",
                    "paddingAll": "10px",
                    "margin": "none"
                },
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
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "📸 กรุณาส่งรูปภาพความเสียหายของรถ",
                    "size": "md",
                    "color": "#FF6B00",
                    "weight": "bold",
                    "margin": "xl",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "เพื่อให้ AI วิเคราะห์และประเมินสิทธิ์การเคลม",
                    "size": "xs",
                    "color": "#999999",
                    "margin": "sm",
                    "wrap": True
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
