from typing import Dict, List, Optional
from linebot.v3.messaging import (
    TextMessage,
    FlexMessage,
    ReplyMessageRequest,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    MessageAction
)
from flex_messages import create_vehicle_selection_flex, create_policy_info_flex

# Dictionary สำหรับเก็บ Session ของผู้ใช้แต่ละคน
# {user_id: {"state": "...", "policy_info": {...}, ...}}
user_sessions: Dict[str, Dict] = {}

def get_session(user_id: str) -> Dict:
    """ดึงข้อมูล session ของผู้ใช้ ถ้าไม่มีให้สร้างใหม่"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {"state": "idle"}
    return user_sessions[user_id]

def set_state(user_id: str, state: str, **kwargs):
    """อัปเดตสถานะและข้อมูลอื่นๆ ใน session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}
    user_sessions[user_id]["state"] = state
    for key, value in kwargs.items():
        user_sessions[user_id][key] = value

def reset_session(user_id: str, initial_state: str = "idle"):
    """รีเซ็ตข้อมูล session"""
    user_sessions[user_id] = {"state": initial_state}

def process_search_result(line_bot_api, event, user_id, policies, use_push=False):
    """
    จัดการผลลัพธ์การค้นหา ส่งข้อความตอบกลับ และอัปเดต state
    ย้ายมาจาก main.py เพื่อให้ Code เป็นระเบียบ
    """
    session = get_session(user_id)

    if not policies:
        msg = TextMessage(text="❌ ไม่พบข้อมูลกรมธรรม์\n\nกรุณาตรวจสอบข้อมูลอีกครั้ง หรือติดต่อเจ้าหน้าที่")
        if use_push:
            line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[msg]))
        else:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[msg]))
        return False

    if len(policies) > 1:
        set_state(user_id, "waiting_for_vehicle_selection", search_results=policies)
        flex_message = create_vehicle_selection_flex(policies)
        msg = FlexMessage(alt_text="กรุณาเลือกรถยนต์", contents=flex_message)
        if use_push:
            line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[msg]))
        else:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=[msg]))
        return True
    else:
        policy_info = policies[0]
        set_state(user_id, "waiting_for_counterpart", policy_info=policy_info)
        
        # แสดงรายละเอียดกรมธรรม์
        flex_policy = create_policy_info_flex(policy_info)
        
        # ถามเรื่องคู่กรณี
        quick_reply = QuickReply(items=[
            QuickReplyItem(action=MessageAction(label="✅ มีคู่กรณี", text="มีคู่กรณี")),
            QuickReplyItem(action=MessageAction(label="❌ ไม่มีคู่กรณี", text="ไม่มีคู่กรณี"))
        ])
        msg_counterpart = TextMessage(
            text="🚘 พบข้อมูลรถยนต์ของคุณแล้ว\n\n❓ **มีคู่กรณีหรือไม่?**\n\nกรุณาเลือก:",
            quick_reply=quick_reply
        )
        
        messages = [
            FlexMessage(alt_text="พบข้อมูลกรมธรรม์", contents=flex_policy),
            msg_counterpart
        ]
        
        if use_push:
            line_bot_api.push_message(PushMessageRequest(to=user_id, messages=messages))
        else:
            line_bot_api.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=messages))
        return True
