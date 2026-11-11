"""Каталог: привязать public_administration к направлению управления.

Гос-управленческая сигнатура (public_administration, management) не имела
ни одного направления с этими key-навыками — модель тянула таких
пользователей в право. Добавляем public_administration в key skills
«Прикладная информатика в управлении корпоративными системами».
Заодно помечаем зависший run 11 как failed.
"""
import sys

sys.path.insert(0, '/app')

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Direction, Feature, ModelRun, ModelRunStatus

db = SessionLocal()
try:
    # 1) Зависший ран — failed
    stuck = db.get(ModelRun, 11)
    if stuck and stuck.status == ModelRunStatus.running:
        stuck.status = ModelRunStatus.failed
        stuck.error_message = 'Отменён (процесс был потерян)'
        db.commit()
        print('RUN11 -> failed')

    # 2) Каталог
    direction = db.scalar(
        select(Direction).where(
            Direction.name == 'Прикладная информатика в управлении корпоративными системами',
        ),
    )
    feature = db.scalar(select(Feature).where(Feature.code == 'public_administration'))
    if direction is None or feature is None:
        print('DIRECTION_OR_FEATURE_NOT_FOUND', bool(direction), bool(feature))
        sys.exit(1)

    if feature in direction.features:
        print('ALREADY_LINKED')
    else:
        direction.features.append(feature)
        db.commit()
        print('LINKED:', direction.name, '+= public_administration')

    print('NEW_SKILLS:', [f.code for f in direction.features])
finally:
    db.close()
