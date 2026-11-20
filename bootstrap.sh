#!/usr/bin/env bash
# Jesus Self - one-shot bootstrap for a small VPS/container (Enzonic, etc.)
# Usage:
#   bash bootstrap.sh
# It installs Python deps and starts the bot with the correct ROLE.
set -e

cd "$(dirname "$0")"

echo "[1/3] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 not found. Install Python 3.11 from the panel's Software tab, then re-run."
  exit 1
fi
python3 --version

echo "[2/3] Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "[3/3] Starting bot..."
export ROLE="${ROLE:-selfonly}"
export SHARD="${SHARD:-0}"
export SHARD_TOTAL="${SHARD_TOTAL:-2}"
export DB_POOL_MIN="${DB_POOL_MIN:-1}"
export DB_POOL_MAX="${DB_POOL_MAX:-4}"
export PYTHONUNBUFFERED=1

# Load .env if present (panel env vars are usually injected directly; this is a fallback)
if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

exec python3 start_all.py
