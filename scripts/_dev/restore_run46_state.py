"""Восстановление состояния на момент рана 46:
- каталог: it_infrastructure снова в key-навыках «Прикладной информатик в управлении»;
- удаление тестовых ранов 47-50 (таблица заканчивается раном 46);
- проверка: последний completed-ран = 46.
"""
import sys

sys.path.insert(0, '/app')

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Direction, Feature, ModelRun

db = SessionLocal()
try:
    direction = db.scalar(
        select(Direction).where(
            Direction.name == 'Прикладная информатика в управлении корпоративными системами',
        ),
    )
    feature = db.scalar(select(Feature).where(Feature.code == 'it_infrastructure'))
    if direction and feature and feature not in direction.features:
        direction.features.append(feature)
        db.commit()
        print('LINKED back: it_infrastructure +=', direction.name)
    else:
        print('CATALOG: уже как при ране 46')

    removed = 0
    for run_id in (47, 48, 49, 50):
        run = db.get(ModelRun, run_id)
        if run:
            db.delete(run)
            removed += 1
    db.commit()
    print(f'Удалено тестовых ранов: {removed}')

    runs = db.query(ModelRun).order_by(ModelRun.id.desc()).limit(3).all()
    for r in runs:
        print(f'RUN {r.id}: {r.status.value} | artifact: {r.artifact_dir[-30:] if r.artifact_dir else "-"}')
finally:
    db.close()
