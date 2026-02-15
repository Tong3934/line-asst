#!/bin/bash

echo "🚀 Starting ngrok..."
python start_ngrok.py &

# รอให้ ngrok เปิดก่อน
sleep 3

echo "🚀 Starting FastAPI..."
python main.py
