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
  echo "[STARTUP] WARNING: .env file not found!"
  echo "[STARTUP] Please create a .env file in the 'app' folder with your secrets."
  echo "[STARTUP] You can copy the template from .env.example."
  exit 1
fi

echo "[STARTUP] Installing requirements..."
pip install --no-cache-dir -r requirements.txt

echo "[STARTUP] Starting Jesus Self..."
exec python3 -u start_all.py
