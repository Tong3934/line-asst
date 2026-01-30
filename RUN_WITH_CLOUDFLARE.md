# 🌐 วิธีรัน LINE Bot ด้วย Cloudflare Tunnel

## ✅ ข้อดีของ Cloudflare Tunnel

- ✅ **ฟรี 100%** - ไม่มี limit, ไม่หมดอายุ
- ✅ **ไม่โดนบล็อค** - Cloudflare เป็น CDN ใหญ่
- ✅ **Stable** - องค์กรใหญ่ใช้
- ✅ **รัน 1 command** - รวมกับ Python
- ✅ **ไม่ต้อง authtoken** - ใช้ได้เลย
- ✅ **Fast** - Network Cloudflare ทั่วโลก

---

## 📦 ขั้นตอนที่ 1: ติดตั้ง cloudflared

### macOS (Homebrew):
```bash
brew install cloudflare/cloudflare/cloudflared
```

### macOS (Manual):
```bash
# Download binary
curl -Lo cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64.tgz

# แตกไฟล์
tar -xzf cloudflared-darwin-amd64.tgz

# ย้ายไปที่ /usr/local/bin
sudo mv cloudflared /usr/local/bin/
sudo chmod +x /usr/local/bin/cloudflared
```

### ตรวจสอบการติดตั้ง:
```bash
cloudflared --version
# ควรเห็น: cloudflared version 2024.x.x
```

---

## 🚀 ขั้นตอนที่ 2: ติดตั้ง Python Dependencies

```bash
pip install -r requirements.txt
```

**หมายเหตุ:** `requirements.txt` ไม่มี pyngrok แล้ว (ใช้ cloudflared แทน)

---

## ⚙️ ขั้นตอนที่ 3: ตั้งค่า Environment Variables

ตรวจสอบไฟล์ `.env`:
```bash
cat .env
```

ควรมี:
```env
LINE_CHANNEL_ACCESS_TOKEN=your_token_here
LINE_CHANNEL_SECRET=your_secret_here
GEMINI_API_KEY=your_api_key_here
PORT=8000
```

---

## 🎯 ขั้นตอนที่ 4: รันโปรแกรม

### วิธีที่ 1: รัน 1 command (แนะนำ ⭐⭐⭐⭐⭐)

```bash
python main-cloud.py
```

**นั่นแหละ! จบ!** โปรแกรมจะ:
1. ✅ สร้าง Cloudflare Tunnel อัตโนมัติ
2. ✅ แสดง Webhook URL
3. ✅ รัน FastAPI server

---

## 📺 Output ที่คาดหวัง:

```
✅ API Key เชื่อมต่อสำเร็จ โมเดลที่ใช้ได้: ['models/gemini-2.0-flash-exp', ...]

======================================================================
⏳ กำลังสร้าง Cloudflare Tunnel...
======================================================================
✅ พบ cloudflared
⏳ กำลังสร้าง tunnel สำหรับ port 8000...

======================================================================
🎉 Cloudflare Tunnel Created Successfully!
======================================================================
📍 Public URL: https://abc-def-123.trycloudflare.com
🔗 Webhook URL (สำหรับ LINE): https://abc-def-123.trycloudflare.com/webhook
======================================================================
📋 คัดลอก URL นี้ไปใส่ใน LINE Developers Console:
   👉 https://abc-def-123.trycloudflare.com/webhook
======================================================================

⚠️  ขั้นตอนต่อไป:
   1. ไปที่: https://developers.line.biz/console/
   2. เลือก Channel ของคุณ
   3. ไปที่: Messaging API > Webhook settings
   4. วาง URL: https://abc-def-123.trycloudflare.com/webhook
   5. กด Verify → ต้องได้ ✅ Success
   6. เปิด 'Use webhook' = ON
======================================================================

💡 หมายเหตุ:
   - Cloudflare Tunnel ฟรีตลอดชีพ
   - URL จะเปลี่ยนทุกครั้งที่รัน
   - กด Ctrl+C เพื่อหยุด
======================================================================

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

## 🔗 ขั้นตอนที่ 5: ตั้งค่า LINE Webhook

1. Copy URL จาก output: `https://abc-def-123.trycloudflare.com/webhook`
2. ไปที่: https://developers.line.biz/console/
3. เลือก Channel
4. ไปที่: **Messaging API** > **Webhook settings**
5. วาง URL: `https://abc-def-123.trycloudflare.com/webhook`
6. กด **Verify** → ต้องได้ ✅ Success
7. เปิด **Use webhook** = ON

---

## 🧪 ขั้นตอนที่ 6: ทดสอบ

1. เพิ่ม LINE Bot เป็นเพื่อน (สแกน QR Code)
2. ส่งข้อความ: "เช็คสิทธิ์เคลมด่วน"
3. ทดสอบ flow ทั้งหมด

---

## 🔧 Troubleshooting

### ❌ ปัญหา: `cloudflared: command not found`
```bash
# ติดตั้งก่อน
brew install cloudflare/cloudflare/cloudflared

# ตรวจสอบ
cloudflared --version
```

### ❌ ปัญหา: "ไม่สามารถดึง URL จาก cloudflared ได้"
```bash
# รันแยกเอง
cloudflared tunnel --url http://localhost:8000

# แล้วรัน Python ใน terminal อื่น
python main-cloud.py
```

### ❌ ปัญหา: Tunnel ช้า
```bash
# เปลี่ยน region (ถ้ารัน manual)
cloudflared tunnel --url http://localhost:8000 --region ap
```

### ❌ ปัญหา: LINE Bot ไม่ตอบ
1. ตรวจสอบ Webhook URL ถูกต้อง (มี `/webhook`)
2. ตรวจสอบ Verify = ✅ Success
3. ตรวจสอบ Use webhook = ON
4. ดู log ใน terminal

---

## 📊 เปรียบเทียบ: Cloudflare vs ngrok

| Feature | **Cloudflare Tunnel** | **ngrok** |
|---------|----------------------|----------|
| ฟรี | ✅ ไม่จำกัด | ⚠️ 2 ชม./session |
| Timeout | ❌ ไม่มี | ✅ มี (free) |
| โดนบล็อค | ⚠️ น้อยมาก | ✅ บ่อย |
| ติดตั้ง | ⭐⭐ | ⭐⭐ |
| Stable | ✅ มาก | ✅ มาก |
| Speed | ✅ เร็ว | ✅ เร็ว |

---

## 🎯 Quick Start (TL;DR)

```bash
# 1. ติดตั้ง cloudflared (ครั้งเดียว)
brew install cloudflare/cloudflare/cloudflared

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. ตั้งค่า .env (ใส่ API Keys)
nano .env

# 4. รัน (1 command เดียวจบ!)
python main-cloud.py

# 5. Copy Webhook URL จาก terminal
# 6. Paste ไปที่ LINE Developers Console
# 7. ทดสอบ!
```

---

## 💡 Tips

### ถ้าต้องการ Fixed URL:
```bash
# Cloudflare ไม่มี fixed URL ใน free tier
# ต้องใช้:
# 1. Cloudflare Tunnel (Paid) + Custom domain
# 2. หรือ Deploy บน Cloud (Railway/Render/GCP)
```

### ถ้ารัน 2 terminals สะดวกกว่า:
```bash
# Terminal 1
python main.py  # (ไฟล์ไม่มี tunnel code)

# Terminal 2
cloudflared tunnel --url http://localhost:8000
```

---

## 🔗 Links

- Cloudflare Tunnel Docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- LINE Developers: https://developers.line.biz/console/
- Download cloudflared: https://github.com/cloudflare/cloudflared/releases

---

**พร้อมใช้งาน! ไม่มีปัญหา SSL, Timeout, หรือ Corporate Firewall** 🎉
