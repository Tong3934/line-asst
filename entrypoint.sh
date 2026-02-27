#!/bin/sh
# entrypoint.sh — container start-up script
# 12-Factor IX (Disposability): fast startup, clean shutdown
set -e

# ── Optional: git-pull from repo (only when REPO_URL is set) ────────────────
if [ -n "${REPO_URL}" ] && [ -n "${BRANCH}" ]; then
  if [ ! -d "/app/.git" ]; then
    echo "📥 First-time clone from ${REPO_URL} (branch: ${BRANCH})..."
    git clone -b "${BRANCH}" "${REPO_URL}" /app
    echo "📦 Installing dependencies..."
    pip install --no-cache-dir -r /app/requirements.txt
  else
    echo "🔄 Pulling latest from ${REPO_URL} (branch: ${BRANCH})..."
    cd /app && git pull origin "${BRANCH}"
  fi
else
  echo "ℹ️  REPO_URL / BRANCH not set — skipping git pull (using baked image code)"
fi

# ── Ensure persistent data directories exist (12-Factor: backing service) ───
DATA_DIR="${DATA_DIR:-/data}"
echo "📂 Initialising data directories at ${DATA_DIR}..."
mkdir -p "${DATA_DIR}/claims"
mkdir -p "${DATA_DIR}/logs"
mkdir -p "${DATA_DIR}/token_records"

# ── Seed sequence.json if absent (first run) ────────────────────────────────
SEQ_FILE="${DATA_DIR}/sequence.json"
if [ ! -f "${SEQ_FILE}" ]; then
  echo '{"CD": 0, "H": 0}' > "${SEQ_FILE}"
  echo "✅ Created ${SEQ_FILE}"
fi

# ── Launch application (12-Factor XI: logs to stdout) ───────────────────────
echo "🚀 Starting LINE Insurance Claim Bot..."
exec python /app/main.py
