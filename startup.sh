#!/usr/bin/env bash
# Enzonic startup script — handles cloning, installing and starting.
set -e

APP_DIR="/home/container/app"
REPO="https://github.com/Batmani26/Jesus-Self.git"

# Ensure we are in the correct directory
cd /home/container

if [ ! -d "$APP_DIR" ]; then
  echo "[STARTUP] Cloning repository..."
  if command -v git >/dev/null 2>&1; then
    git clone "$REPO" "$APP_DIR"
  else
    echo "[STARTUP] ERROR: git not found. Please clone manually or upload files."
    exit 1
  fi
fi

if [ ! -d "$APP_DIR" ]; then
  echo "[STARTUP] ERROR: Could not create app directory. Check permissions."
  exit 1
fi

cd "$APP_DIR"

if [ -f ".env" ]; then
  echo "[STARTUP] Loading env vars from .env..."
  set -a
  source .env
  set +a
else
  echo "[STARTUP] WARNING: .env file not found. Using environment variables from the panel instead."
  echo "[STARTUP] Make sure ROLE, SHARD, DATABASE_URL, ENCRYPTION_KEY, BOT_TOKEN, API_ID, API_HASH are set in the panel's Environment Variables section."
fi

echo "[STARTUP] Installing requirements..."
pip install --no-cache-dir -r requirements.txt

echo "[STARTUP] Starting Jesus Self..."
exec python3 -u start_all.py
