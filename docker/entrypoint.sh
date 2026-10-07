#!/bin/sh
set -e

echo ">>> Применение миграций (если есть) ..."
alembic upgrade head 2>/dev/null || echo "    (версий миграций нет — пропуск)"

echo ">>> Сид конфигурации (идемпотентно) ..."
python scripts/seed.py

echo ">>> Миграция старых CSV-ответов (если есть) ..."
python scripts/migrate_responses.py data/real/responses.csv || true

echo ">>> Запуск CareerAI Platform на ${HOST:-0.0.0.0}:${PORT:-7777}"
exec python -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-7777}"
