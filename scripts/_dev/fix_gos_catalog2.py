"""Каталог: отвязать it_infrastructure от направления управления.

it_infrastructure в key-навыках «Прикладной информатик в управлении
корпоративными системами» мешает: у гос-профиля он низкий, и модель
не активирует класс. Оставляем ba + management + public_administration.
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
    if direction is None or feature is None:
        print('NOT_FOUND')
        sys.exit(1)
    if feature in direction.features:
        direction.features.remove(feature)
        db.commit()
        print('UNLINKED: it_infrastructure removed from', direction.name)
    else:
        print('ALREADY_ABSENT')
    print('NEW_SKILLS:', [f.code for f in direction.features])
finally:
    db.close()
