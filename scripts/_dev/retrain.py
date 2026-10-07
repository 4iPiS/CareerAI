"""DEV-утилита: повторный запуск обучения модели (после падения/отмены).

Переехала из корня проекта в scripts/_dev/ при реструктуризации.
Запуск: python scripts/_dev/retrain.py
"""
from app.database import SessionLocal
from app.models import ModelRun, ModelRunStatus
from app.services.trainer import run_training

db = SessionLocal()
run = db.query(ModelRun).filter(ModelRun.status == ModelRunStatus.failed).order_by(ModelRun.id.desc()).first()
if run:
    run.status = ModelRunStatus.pending
    run.finished_at = None
    run.error_message = ''
    db.commit()
    run_id = run.id
    print(f'Возобновляю run {run_id}')
else:
    run = ModelRun(status=ModelRunStatus.pending, triggered_by=1, config_snapshot={})
    db.add(run)
    db.commit()
    run_id = run.id
    print(f'Создан новый run {run_id}')
db.close()

print('Начинаю обучение (~165K образцов)...')
run_training(run_id, triggered_by=1, dataset='synthetic')
print(f'Готово run={run_id}')