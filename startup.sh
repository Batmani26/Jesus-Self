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

if [ ! -f ".env" ]; then
  echo "[STARTUP] ERROR: .env file not found in app folder. Please create it."
  exit 1
fi

echo "[STARTUP] Loading env vars from .env..."
set -a
source .env
set +a

echo "[STARTUP] Installing requirements..."
pip install --no-cache-dir -r requirements.txt

echo "[STARTUP] Starting Jesus Self..."
exec python3 -u start_all.py
