#!/bin/sh
set -e

MODEL_FILE="/app/career_model/career_model.keras"

if [ ! -f "$MODEL_FILE" ]; then
  echo ">>> Модель не найдена ($MODEL_FILE)."
  echo ">>> Обучение при первом запуске (может занять несколько минут)..."
  python train_model.py
fi

echo ">>> Запуск CareerAI на ${HOST:-0.0.0.0}:${PORT:-7777}"
exec python -m uvicorn main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-7777}"
