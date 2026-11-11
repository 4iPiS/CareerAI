#!/usr/bin/env python3
"""Перегенерация датасета (ЕГЭ 1-5) + переобучение модели.

Запуск: python scripts/retrain_v2.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models import ModelRun, ModelRunStatus
from app.services.trainer import generate_dataset_csv, run_training

print("=== Шаг 1: Перегенерация датасета (ЕГЭ 1-5) ===")
db = SessionLocal()
try:
    output = Path("data/training_synthetic.csv")
    info = generate_dataset_csv(db, output)
    print(f"  Сгенерировано: {info['rows']} строк")
    print(f"  Признаков: {len(info['features'])}")
    print(f"  Направлений: {len(info['directions'])}")
finally:
    db.close()

print("\n=== Шаг 2: Обучение модели ===")
db = SessionLocal()
try:
    run = ModelRun(status=ModelRunStatus.pending, triggered_by=1, config_snapshot={})
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id
    print(f"  Создан run {run_id}")
finally:
    db.close()

print(f"  Запуск обучения run={run_id} ...")
run_training(run_id, triggered_by=1, dataset='synthetic')

print(f"\n=== Готово run={run_id} ===")
