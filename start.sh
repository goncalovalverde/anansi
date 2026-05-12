#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing Python dependencies..."
pip install -r "$ROOT_DIR/requirements.txt" --quiet

FRONTEND_DIST="$ROOT_DIR/frontend-vue/dist"
if [ ! -d "$FRONTEND_DIST" ]; then
  echo "==> Building frontend (first run)..."
  cd "$ROOT_DIR/frontend-vue"
  npm install --silent
  npm run build
  cd "$ROOT_DIR"
fi

echo "==> Starting Anansi backend on http://localhost:9000"
cd "$ROOT_DIR"
uvicorn backend.main:app --reload --port 9000
