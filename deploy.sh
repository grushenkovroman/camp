#!/usr/bin/env bash
# Деплой camp.rasti24.ru на сервер.
# Использование: ./deploy.sh
set -euo pipefail

REMOTE_USER="grushenkov"
REMOTE_HOST="84.22.133.11"
REMOTE_PATH="/home/grushenkov/projects/camp-program"
SERVICE_NAME="camp-rasti"

echo "→ синхронизирую код на ${REMOTE_HOST}:${REMOTE_PATH}"
rsync -av --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"

echo "→ устанавливаю зависимости и перезапускаю сервис"
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash -lc "'
  set -euo pipefail
  cd ${REMOTE_PATH}
  if [ ! -d .venv ]; then
    python3 -m venv .venv
  fi
  ./.venv/bin/pip install --upgrade pip --quiet
  ./.venv/bin/pip install -r requirements.txt --quiet
  ./.venv/bin/python manage.py schema
  sudo systemctl restart ${SERVICE_NAME}
  sudo systemctl status ${SERVICE_NAME} --no-pager | head -10
'"

echo "→ готово: https://camp.rasti24.ru/"
