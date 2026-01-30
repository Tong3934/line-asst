# 🚀 วิธีรัน LINE Bot บน Local

## ✅ ขั้นตอนที่ 1: ตรวจสอบ Requirements

### 1.1 ติดตั้ง Python 3.11+
```bash
python --version
# ควรได้: Python 3.11.x หรือสูงกว่า
```

### 1.2 ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

---

## ✅ ขั้นตอนที่ 2: ตั้งค่า Environment Variables

### 2.1 ตรวจสอบไฟล์ `.env`
```bash
cat .env
```

ควรมีรูปแบบนี้:
```env
# LINE Messaging API Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
LINE_CHANNEL_SECRET=your_channel_secret_here

# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Server Configuration (Optional)
PORT=8000
```

### 2.2 ถ้ายังไม่มี → สร้างไฟล์ `.env` ใหม่
```bash
cp .env.example .env
# แล้วแก้ไขใส่ค่าจริง
```

---

## ✅ ขั้นตอนที่ 3: รัน Server

### 3.1 รันด้วย Python
```bash
python main.py
```

### 3.2 หรือรันด้วย Uvicorn (แนะนำ)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Options:**
- `--reload` = Auto-reload เมื่อแก้ไขโค้ด
- `--port 8000` = เปลี่ยน port ได้

---

## ✅ ขั้นตอนที่ 4: ตรวจสอบว่า Server ทำงาน

### 4.1 เปิดเว็บเบราว์เซอร์
```
http://localhost:8000
```

ควรเห็น:
```json
{
  "message": "LINE Insurance Claim Bot API",
  "status": "running",
  "version": "1.0.0"
}
```

### 4.2 ตรวจสอบ Health Check
```
http://localhost:8000/health
```

ควรเห็น:
```json
{
  "status": "healthy",
  "line_configured": true,
  "gemini_configured": true
}
```

---

## ✅ ขั้นตอนที่ 5: เชื่อมต่อกับ LINE

### 5.1 ติดตั้ง ngrok (สำหรับ Webhook)
```bash
# macOS (Homebrew)
brew install ngrok

# หรือดาวน์โหลดจาก https://ngrok.com/download
```

### 5.2 รัน ngrok
```bash
ngrok http 8000
```

จะได้ URL แบบนี้:
```
https://abc123.ngrok.io
```

### 5.3 ตั้งค่า Webhook URL ใน LINE Developers
1. ไปที่ https://developers.line.biz/console/
2. เลือก Channel ของคุณ
3. ไปที่ **Messaging API** > **Webhook settings**
4. ใส่ URL: `https://abc123.ngrok.io/webhook`
5. กด **Verify** → ควรได้ ✅ Success
6. เปิด **Use webhook** = ON

---

## ✅ ขั้นตอนที่ 6: ทดสอบ

### 6.1 เพิ่ม LINE Bot เป็นเพื่อน
1. สแกน QR Code จาก LINE Developers Console
2. Add Friend

### 6.2 ส่งข้อความทดสอบ
```
ผู้ใช้: เช็คสิทธิ์เคลมด่วน
Bot: [แสดง Flex Message ขอข้อมูล]

ผู้ใช้: สมชาย เข็มกลัด, 1กข1234
Bot: [ถามคู่กรณี]

ผู้ใช้: [กดปุ่ม "มีคู่กรณี"]
Bot: [แสดงข้อมูลกรมธรรม์ และขอรูปภาพ]

ผู้ใช้: [ส่งรูปภาพ]
Bot: [วิเคราะห์ด้วย AI และแสดงผลพร้อมปุ่มโทร]
```

---

## 🔧 Troubleshooting

### ❌ ปัญหา: `ModuleNotFoundError`
```bash
# แก้: ติดตั้ง dependencies ใหม่
pip install -r requirements.txt
```

### ❌ ปัญหา: `ValueError: กรุณาตั้งค่า Environment Variables`
```bash
# แก้: ตรวจสอบไฟล์ .env
cat .env

# ต้องมีค่าครบทั้ง 3 ตัว:
# LINE_CHANNEL_ACCESS_TOKEN=...
# LINE_CHANNEL_SECRET=...
# GEMINI_API_KEY=...
```

### ❌ ปัญหา: ngrok ใช้ไม่ได้
```bash
# แก้: ใช้ Cloudflare Tunnel แทน
npm install -g cloudflared
cloudflared tunnel --url http://localhost:8000
```

### ❌ ปัญหา: LINE Bot ไม่ตอบ
1. ตรวจสอบ Webhook URL ว่าถูกต้อง
2. ตรวจสอบ ngrok ยังทำงานอยู่หรือไม่
3. ดู log ใน terminal ว่ามี error อะไร

### ❌ ปัญหา: AI ไม่วิเคราะห์รูป
```bash
# ตรวจสอบ Gemini API Key
# 1. ไปที่ https://makersuite.google.com/app/apikey
# 2. สร้าง API Key ใหม่
# 3. ใส่ใน .env
```

---

## 📊 ตัวอย่าง Log ที่ถูกต้อง

```
✅ API Key เชื่อมต่อสำเร็จ โมเดลที่ใช้ได้: ['models/gemini-2.0-flash-exp', 'models/gemini-1.5-flash', ...]
============================================================
🚀 LINE Insurance Claim Bot Starting...
============================================================
📍 Server: http://localhost:8000
🔗 Webhook: http://localhost:8000/webhook
❤️  Health: http://localhost:8000/health
============================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🎯 Quick Start (TL;DR)

```bash
# 1. ติดตั้ง dependencies
pip install -r requirements.txt

# 2. ตั้งค่า .env (ใส่ API Keys)
nano .env

# 3. รัน server
python main.py

# 4. (ใน terminal ใหม่) รัน ngrok
ngrok http 8000

# 5. ตั้งค่า Webhook URL ใน LINE Developers
# URL: https://xxx.ngrok.io/webhook

# 6. ทดสอบ!
```

---

## 📝 หมายเหตุ

- **Development**: ใช้ ngrok (ฟรี, ง่าย, แต่ URL เปลี่ยนทุกครั้งที่รัน)
- **Production**: ใช้ VPS/Cloud Server พร้อม domain จริง
- **Port**: Default = 8000, เปลี่ยนได้ใน `.env` หรือ `--port`
- **Auto-reload**: เปิด `--reload` ใน uvicorn (dev only)

---

## 🔗 Links

- LINE Developers Console: https://developers.line.biz/console/
- ngrok: https://ngrok.com/
- Google Gemini API: https://makersuite.google.com/app/apikey

---

**Happy Coding! 🚀**
