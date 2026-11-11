"""Фоновое переобучение: создать ран и обучить на синтетике (контейнер)."""
import sys

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import ModelRun, ModelRunStatus
from app.services.trainer import run_training

db = SessionLocal()
run = ModelRun(
    status=ModelRunStatus.pending,
    triggered_by=None,
    config_snapshot={'dataset_type': 'synthetic'},
    total_epochs=80,
)
db.add(run)
db.commit()
db.refresh(run)
run_id = run.id
db.close()
print('RUN_ID', run_id, flush=True)
run_training(run_id, None, dataset='synthetic', real_data_path=None, model_id=None)
print('DONE', flush=True)
