#!/bin/bash

# Script สำหรับเริ่ม Cloudflare Tunnel
# ใช้สำหรับเชื่อมต่อ Local Server กับ LINE Webhook

echo "========================================================================"
echo "🌐 Starting Cloudflare Tunnel..."
echo "========================================================================"

# ตรวจสอบว่าติดตั้ง cloudflared แล้วหรือไม่
if ! command -v cloudflared &> /dev/null; then
    echo ""
    echo "❌ ไม่พบ cloudflared!"
    echo ""
    echo "💡 กรุณาติดตั้งก่อน:"
    echo "   brew install cloudflare/cloudflare/cloudflared"
    echo ""
    echo "หรือดาวน์โหลดจาก:"
    echo "   https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
    echo ""
    exit 1
fi

# แสดงเวอร์ชัน
CLOUDFLARED_VERSION=$(cloudflared --version)
echo "✅ พบ cloudflared: $CLOUDFLARED_VERSION"
echo ""

# ดึงค่า PORT จาก .env (ถ้ามี)
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep PORT | xargs)
fi

# ใช้ PORT จาก .env หรือ default 8000
PORT=${PORT:-8000}

echo "⏳ กำลังสร้าง tunnel สำหรับ http://localhost:$PORT ..."
echo ""
echo "⚠️  คำเตือน:"
echo "   - ต้องรัน Python Server (main.py หรือ main-cloud.py) ก่อน!"
echo "   - ตรวจสอบว่า server รันที่ port $PORT"
echo ""
echo "========================================================================"

# รัน cloudflared tunnel
cloudflared tunnel --url http://localhost:$PORT

# หมายเหตุ: Script นี้จะรันต่อเนื่องจนกว่าจะกด Ctrl+C
