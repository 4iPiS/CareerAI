"""Активировать артефакты run 46 как последнюю модель.

Раны нумеруются подряд по всем запускам (админка + фоновые итерации).
Recommender всегда берёт последний completed-ран, поэтому создаём новый
ран-«клон» с артефактами и метриками run 46 — он становится активным.
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/app')

from app.config import get_settings
from app.database import SessionLocal
from app.models import ModelRun, ModelRunStatus

SOURCE_RUN_ID = 46

db = SessionLocal()
try:
    src = db.get(ModelRun, SOURCE_RUN_ID)
    if src is None or src.status != ModelRunStatus.completed:
        print(f'RUN {SOURCE_RUN_ID} не найден или не завершён')
        sys.exit(1)

    settings = get_settings()
    new_dir = Path(settings.models_dir) / f'run_{src.id}_active'
    if new_dir.exists():
        shutil.rmtree(new_dir)
    shutil.copytree(src.artifact_dir, new_dir)
    print('Артефакты скопированы:', new_dir)

    clone = ModelRun(
        status=ModelRunStatus.completed,
        config_snapshot=src.config_snapshot,
        metrics=src.metrics,
        artifact_dir=str(new_dir),
        triggered_by=None,
        current_epoch=src.current_epoch,
        total_epochs=src.total_epochs,
        finished_at=datetime.now(),
        error_message='',
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    print(f'АКТИВИРОВАН: новый ран #{clone.id} c артефактами run #{SOURCE_RUN_ID}')
    print('top1:', (clone.metrics or {}).get('top1_accuracy'))
finally:
    db.close()
