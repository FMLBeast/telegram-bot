#!/usr/bin/env bash
set -euo pipefail

# sync_env.sh
# Upload local .env to VPS and restart the bot service

VPS_HOST="${VPS_HOST:-194.31.143.17}"
VPS_USER="${VPS_USER:-ubuntu}"
SSH_KEY_PATH="${SSH_KEY_PATH:-$HOME/.ssh/server_key}"
APP_DIR="${APP_DIR:-/opt/telegram-bot}"
ENV_FILE="$APP_DIR/.env"
SERVICE_NAME="${SERVICE_NAME:-telegram-bot}"

LOCAL_ENV_PATH="${LOCAL_ENV_PATH:-.env}"   # path to your local .env

if [ ! -f "$LOCAL_ENV_PATH" ]; then
  echo "Local .env not found at $LOCAL_ENV_PATH" >&2
  exit 1
fi

echo "==> Uploading $LOCAL_ENV_PATH to $VPS_USER@$VPS_HOST:$ENV_FILE ..."
scp -i "$SSH_KEY_PATH" "$LOCAL_ENV_PATH" "$VPS_USER@$VPS_HOST:/tmp/.env.tmp"

ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_HOST" bash -s <<'SSH'
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/telegram-bot}"
ENV_FILE="$APP_DIR/.env"
SERVICE_NAME="${SERVICE_NAME:-telegram-bot}"

sudo mkdir -p "$APP_DIR"
sudo mv /tmp/.env.tmp "$ENV_FILE"
sudo chown ubuntu:ubuntu "$ENV_FILE"
sudo chmod 600 "$ENV_FILE"

sudo systemctl daemon-reload || true
sudo systemctl restart "$SERVICE_NAME" || sudo systemctl start "$SERVICE_NAME"
sudo systemctl status "$SERVICE_NAME" --no-pager || true
echo "----- Last 40 logs -----"
sudo journalctl -u "$SERVICE_NAME" -n 40 --no-pager || true
SSH

echo "==> Done. .env synced and service restarted."
