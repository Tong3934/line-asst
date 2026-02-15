#!/bin/sh
set -e

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

echo "🚀 Starting bot..."
exec python /app/main.py
