#!/bin/sh

set -e

REPO_URL=${REPO_URL:-""}
BRANCH=${BRANCH:-main}
APP_DIR=/app/src

echo "🚀 Starting container..."

# clone ครั้งแรก
if [ ! -d "$APP_DIR" ]; then
  echo "📥 Cloning repo..."
  git clone -b $BRANCH $REPO_URL $APP_DIR
else
  echo "🔄 Pulling latest code..."
  cd $APP_DIR
  git pull origin $BRANCH
fi

cd $APP_DIR

# install requirements ถ้ามี
if [ -f requirements.txt ]; then
  echo "📦 Installing requirements..."
  pip install --no-cache-dir -r requirements.txt
fi

echo "▶️ Starting FastAPI..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
