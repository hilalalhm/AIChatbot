#!/usr/bin/env bash
# Deployment script for Jagoan Hosting (cPanel "Setup Python App").
# See README for configuration via .env / GitHub secrets.
set -euo pipefail

# Configurable values (override via environment)
DEPLOY_PATH="${DEPLOY_PATH:-}"
RESTART_CMD="${RESTART_CMD:-}"
VENV_BIN="${VENV_BIN:-/home/jasanika/virtualenv/apps/AIChatBot/3.12/bin}"

if [[ -z "$DEPLOY_PATH" ]]; then
    echo "ERROR: DEPLOY_PATH is not set." >&2
    exit 1
fi

echo "==> Entering project directory: $DEPLOY_PATH"
cd "$DEPLOY_PATH"

echo "==> Updating code"
git pull --ff-only || { echo "ERROR: git pull failed" >&2; exit 1; }

echo "==> Installing dependencies"
"$VENV_BIN/pip" install -r requirements.txt

echo "==> Running migrations (if required)"
if [[ -x "$VENV_BIN/alembic" ]]; then
    "$VENV_BIN/alembic" upgrade head
else
    echo "alembic not available; skipping migrations. Ensure DB is initialized by the app on startup."
fi

if [[ -n "$RESTART_CMD" ]]; then
    echo "==> Restarting application"
    eval "$RESTART_CMD"
else
    echo "WARNING: RESTART_CMD not set. Please restart the Python app manually from cPanel."
fi

echo "==> Deployment completed successfully."
