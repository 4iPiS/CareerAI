"""Каталог: it_infrastructure больше не key-навык направления управления
(у гос-профиля он низкий и штрафует класс). Key: ba + management + pa.
"""
import sys

sys.path.insert(0, '/app')

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Direction, Feature

db = SessionLocal()
try:
    direction = db.scalar(
        select(Direction).where(
            Direction.name == 'Прикладная информатика в управлении корпоративными системами',
        ),
    )
    feature = db.scalar(select(Feature).where(Feature.code == 'it_infrastructure'))
    if direction and feature and feature in direction.features:
        direction.features.remove(feature)
        db.commit()
        print('UNLINKED it_infrastructure')
    else:
        print('ALREADY_ABSENT')
    print('SKILLS:', [f.code for f in direction.features])
finally:
    db.close()
