"""Общие фикстуры для тестов платформы (SQLite in-memory + полный сид)."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.base import Base


@pytest.fixture()
def db_session():
    # StaticPool + check_same_thread=False — единое соединение для всех потоков
    # (нужно, т.к. TestClient выполняет запросы в других потоках).
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    db = Session()
    yield db
    db.close()
    engine.dispose()


def _run_config_pipeline(db):
    """Прогоняет стартовые скрипты конфигурации (как docker/entrypoint.sh):
    add_ege → sync_directions → add_program_features.

    Каждый скрипт открывает собственную сессию через SessionLocal, поэтому
    подменяем фабрику на новую сессию поверх того же in-memory engine
    (StaticPool даёт общее соединение, коммиты видны всем сессиям).
    """
    import scripts.add_ege as add_ege_mod
    import scripts.add_program_features as apf_mod
    import scripts.sync_directions as sync_mod

    engine = db.get_bind()
    Session = sessionmaker(bind=engine, future=True)

    for mod in (add_ege_mod, sync_mod, apf_mod):
        original = mod.SessionLocal
        mod.SessionLocal = lambda: Session()
        try:
            mod.main()
        finally:
            mod.SessionLocal = original


@pytest.fixture()
def seeded_db(db_session):
    from scripts import seed

    features = seed.seed_features(db_session)
    seed.seed_directions(db_session, features)
    groups = seed.seed_question_groups(db_session)
    seed.seed_questions(db_session, groups, features)
    seed.seed_university_settings(db_session)
    seed.seed_admin(db_session)
    db_session.commit()

    # Полный пайплайн конфигурации продакшена:
    # 11 признаков ЕГЭ + 31 программа (профили) + привязка новых навыков.
    _run_config_pipeline(db_session)
    db_session.expire_all()
    return db_session