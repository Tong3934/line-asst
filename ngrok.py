import os
import nest_asyncio
from pyngrok import ngrok
from dotenv import load_dotenv

# โหลดค่า .env
load_dotenv()

# อ่านค่า NGROK_AUTH_TOKEN
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

if not NGROK_AUTH_TOKEN:
    raise ValueError("❌ NGROK_AUTH_TOKEN not found in environment")

# ตั้งค่า auth token
ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# ปิด tunnel เก่าก่อน
ngrok.kill()

# เปิด tunnel ไปที่ port 8000
ngrok_tunnel = ngrok.connect(8000)

# แสดง webhook URL
print(f"✅ Public URL สำหรับ LINE Webhook: {ngrok_tunnel.public_url}/webhook")

# สำหรับกรณีรันใน environment ที่มี event loop อยู่แล้ว (เช่น Colab)
nest_asyncio.apply()
