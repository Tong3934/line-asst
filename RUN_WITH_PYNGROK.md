# 🚀 วิธีรัน LINE Bot ด้วย pyngrok

## ✅ ข้อดีของ pyngrok
- ✅ **รัน 1 command เดียว** - ไม่ต้องเปิด terminal แยก
- ✅ **Auto URL Display** - แสดง Webhook URL อัตโนมัติ
- ✅ **Python Native** - จัดการ error ได้ดีกว่า
- ✅ **ง่ายกว่า ngrok CLI** - ไม่ต้องติดตั้งแยก

---

## 📦 ขั้นตอนที่ 1: ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

ตรวจสอบว่ามี `pyngrok==7.0.5` ใน requirements.txt แล้ว

---

## 🔑 ขั้นตอนที่ 2: ตั้งค่า Environment Variables

### ตรวจสอบไฟล์ `.env`:
```bash
cat .env
```

**ต้องมี:**
```env
# LINE Messaging API Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_CHANNEL_SECRET=your_secret_here

# Google Gemini API Configuration
GEMINI_API_KEY=your_api_key_here

# Server Configuration
PORT=8000

# ngrok Configuration (Optional - แนะนำให้ใส่)
NGROK_AUTH_TOKEN=your_ngrok_token_here
```

### 📝 วิธีหา NGROK_AUTH_TOKEN (ฟรี):
1. สมัครที่: https://dashboard.ngrok.com/signup
2. ไปที่: https://dashboard.ngrok.com/get-started/your-authtoken
3. Copy token มาใส่ใน `.env`

**ข้อดีของการใส่ token:**
- ✅ Tunnel อายุยาวขึ้น (8 ชม.)
- ✅ ได้ fixed domain (paid plan)
- ✅ ดู dashboard traffic ได้

---

## 🚀 ขั้นตอนที่ 3: รันโปรแกรม

```bash
python main.py
```

**นั่งนี่แหละ! 1 command เดียวจบ** ✨

---

## 📺 Output ที่คาดหวัง:

```
✅ API Key เชื่อมต่อสำเร็จ โมเดลที่ใช้ได้: ['models/gemini-2.0-flash-exp', ...]
============================================================
🌐 ngrok Tunnel Created!
============================================================
🔗 Public URL: https://abc123-456-def.ngrok-free.app
📋 Webhook URL: https://abc123-456-def.ngrok-free.app/webhook
============================================================
⚠️  Copy Webhook URL ไปตั้งค่าใน LINE Developers Console
============================================================
============================================================
🚀 LINE Insurance Claim Bot Starting...
============================================================
📍 Local Server: http://localhost:8000
🔗 Local Webhook: http://localhost:8000/webhook
❤️  Health Check: http://localhost:8000/health
============================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🔗 ขั้นตอนที่ 4: ตั้งค่า Webhook URL

### 4.1 Copy Webhook URL
จาก output ด้านบน copy URL ที่ขึ้นต้นด้วย `https://...ngrok-free.app/webhook`

### 4.2 ไปที่ LINE Developers Console
1. เปิด: https://developers.line.biz/console/
2. เลือก Channel ของคุณ
3. ไปที่: **Messaging API** > **Webhook settings**
4. วาง Webhook URL: `https://abc123-456-def.ngrok-free.app/webhook`
5. กด **Verify** → ต้องได้ ✅ **Success**
6. เปิด **Use webhook** = **ON**

### 4.3 เปิดการรับข้อความ
- ไปที่ **Messaging API** > **LINE Official Account features**
- เปิด **Allow bot to join group chats** = ON (ถ้าต้องการ)
- **Auto-reply messages** = OFF (ปิดเพื่อให้ bot ของเราทำงาน)

---

## 🧪 ขั้นตอนที่ 5: ทดสอบ

### 5.1 เพิ่ม LINE Bot เป็นเพื่อน
1. สแกน QR Code จาก LINE Developers Console
2. Add Friend

### 5.2 ทดสอบ Flow
```
1. ผู้ใช้: "เช็คสิทธิ์เคลมด่วน"
   Bot: [Flex Message ขอข้อมูล]

2. ผู้ใช้: "สมชาย เข็มกลัด, 1กข1234"
   Bot: [ถามคู่กรณี - ปุ่ม: มีคู่กรณี / ไม่มีคู่กรณี]

3. ผู้ใช้: [กดปุ่ม "มีคู่กรณี"]
   Bot: [แสดงข้อมูลกรมธรรม์ + ขอรูปภาพ]

4. ผู้ใช้: [ส่งรูปภาพความเสียหาย]
   Bot: [⏳ กำลังวิเคราะห์... 10-30 วินาที]

5. Bot: [แสดงผลการวิเคราะห์ พร้อมปุ่มโทรออก 📞]
```

---

## 🔧 Troubleshooting

### ❌ ปัญหา: `ModuleNotFoundError: No module named 'pyngrok'`
```bash
pip install pyngrok
# หรือ
pip install -r requirements.txt
```

### ❌ ปัญหา: `PyngrokNgrokHTTPError: ERR_NGROK_108`
**สาเหตุ:** Session limit exceeded (free plan = 1 tunnel พร้อมกัน)

**วิธีแก้:**
```bash
# ปิด ngrok process เก่า
pkill ngrok

# หรือ restart เครื่อง
# แล้วรันใหม่
python main.py
```

### ❌ ปัญหา: `⚠️ ngrok error: ...`
**สาเหตุ:** ไม่มี ngrok authtoken หรือ network error

**วิธีแก้:**
1. ใส่ `NGROK_AUTH_TOKEN` ใน `.env`
2. ตรวจสอบ internet connection
3. ลอง restart

**หมายเหตุ:** แม้ไม่มี token ก็รันได้ แต่จะรัน **local only** (ไม่มี public URL)

### ❌ ปัญหา: LINE Bot ไม่ตอบ
**ตรวจสอบ:**
1. ✅ Webhook URL ถูกต้อง (มี `/webhook` ท้าย)
2. ✅ Verify แล้ว (ติ๊กเขียว)
3. ✅ Use webhook = ON
4. ✅ Auto-reply messages = OFF
5. ✅ Terminal ยังรันอยู่ (ไม่ปิด)

**ดู Log:**
- ใน terminal จะเห็น request เข้ามา
- ถ้าไม่มี = Webhook URL ผิด
- ถ้ามี error = ดู error message

---

## 💡 เคล็ดลับ

### 🔄 Restart โปรแกรม
```bash
# กด Ctrl+C เพื่อหยุด
# แล้วรันใหม่
python main.py
```

**หมายเหตุ:** URL จะเปลี่ยนทุกครั้งที่รัน (ต้องอัพเดท Webhook URL ใหม่)

### 🎯 Fixed Domain (Paid Plan)
ถ้าไม่อยากเปลี่ยน URL ทุกครั้ง:
1. Upgrade ngrok to paid plan
2. ตั้ง custom domain
3. Webhook URL จะเหมือนเดิมตลอด

---

## 📊 เปรียบเทียบ Free vs Paid

| Feature | **Free** | **Paid** |
|---------|----------|----------|
| Tunnels | 1 พร้อมกัน | 3+ พร้อมกัน |
| Domain | Random | Custom |
| Timeout | 2 ชม. | 8 ชม.+ |
| Dashboard | Basic | Advanced |
| ราคา | ฟรี | $8/เดือน |

**แนะนำ:** ใช้ Free ก่อนเพื่อทดสอบ ถ้าใช้งานจริง -> Paid

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. ติดตั้ง
pip install -r requirements.txt

# 2. ตั้งค่า .env (ใส่ API Keys)
nano .env

# 3. รัน (1 command เดียว!)
python main.py

# 4. Copy Webhook URL จาก terminal
# 5. Paste ไปที่ LINE Developers Console
# 6. ทดสอบ!
```

---

## 🔗 Links

- LINE Developers: https://developers.line.biz/console/
- ngrok Dashboard: https://dashboard.ngrok.com/
- ngrok Signup: https://dashboard.ngrok.com/signup
- Google Gemini API: https://makersuite.google.com/app/apikey

---

**Happy Coding with pyngrok! 🎉**
