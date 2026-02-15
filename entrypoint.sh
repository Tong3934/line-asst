#!/bin/sh
set -e

# 📥 clone repo ครั้งแรก
if [ ! -d "/app/.git" ]; then
  echo "📥 First time clone..."
  git clone -b ${BRANCH} ${REPO_URL} /app

  echo "📦 Installing dependencies (first time)..."
  pip install --no-cache-dir -r /app/requirements.txt
else
  echo "🔄 Repo exists, pulling latest..."
  cd /app
  git pull
fi

cd /app

echo "🚀 Starting ngrok..."
python start_ngrok.py &

# รอ tunnel ขึ้นก่อน
sleep 3

echo "🚀 Starting FastAPI..."
exec python main.py
