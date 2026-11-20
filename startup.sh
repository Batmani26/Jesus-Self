#!/usr/bin/env bash
# Enzonic startup script — handles cloning, installing and starting.
set -e

APP_DIR="/home/container/app"
REPO="https://github.com/Batmani26/Jesus-Self.git"

if [ ! -d "$APP_DIR" ]; then
  echo "[STARTUP] Cloning repository..."
  git clone "$REPO" "$APP_DIR"
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
