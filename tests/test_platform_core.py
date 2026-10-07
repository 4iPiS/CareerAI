"""Тесты ядра платформы: сид, движок опросника, рекомендатель."""

from sqlalchemy import func, select

from app.models import Direction, Feature, Question, SurveySession
from app.services.questionnaire import SurveyEngine
from app.services.recommender import Recommender, get_match_level


def test_seed_counts(seeded_db):
    features = seeded_db.scalar(select(func.count()).select_from(Feature))
    directions_total = seeded_db.scalar(select(func.count()).select_from(Direction))
    directions_active = seeded_db.scalar(
        select(func.count())
        .select_from(Direction)
        .where(Direction.is_active.is_(True)),
    )
    questions = seeded_db.scalar(select(func.count()).select_from(Question))
    # Полный пайплайн продакшена: 32 базовых + 11 признаков ЕГЭ
    assert features == 43
    # Активные программы (профили) с сайта вуза
    assert directions_active == 31
    # Старые агрегаты деактивированы, но не удалены (история рекомендаций читаема)
    assert directions_total > 31
    assert questions > 80  # скрининг + цепочки + личные + зарплата + ЕГЭ


def test_seed_is_idempotent(seeded_db):
    from scripts import seed

    features = seed.seed_features(seeded_db)
    seed.seed_directions(seeded_db, features)
    groups = seed.seed_question_groups(seeded_db)
    seed.seed_questions(seeded_db, groups, features)
    seeded_db.commit()

    assert seeded_db.scalar(select(func.count()).select_from(Question)) > 80


def _run_flow(engine, stop_at_custom: bool):
    """Проводит опрос до конца (или до анкеты custom), отвечая по шаблону."""
    state = engine.start_state()
    payload = engine.first_payload(state)
    steps = 0
    while payload is not None and steps < 300:
        if stop_at_custom and payload.get('is_custom'):
            break
        if payload.get('is_ege_select'):
            answer = ['ege_math', 'ege_russian', 'ege_physics']
        elif payload.get('is_ege'):
            answer = {s['code']: 80 for s in payload.get('subjects', [])}
        elif payload.get('is_salary'):
            answer = 100000
        else:
            answer = 3
        payload, state = engine.submit_answer(state, payload['id'], answer)
        steps += 1
    return payload, state


def test_full_questionnaire_flow(seeded_db):
    engine = SurveyEngine(seeded_db)
    payload, state = _run_flow(engine, stop_at_custom=False)

    assert payload is None  # опрос завершён (кастомных полей нет)

    profile = engine.build_profile(state)
    assert profile['desired_salary'] == 100000
    feature_count = seeded_db.scalar(select(func.count()).select_from(Feature))
    assert len(profile) == feature_count
    # все признаки получили значения (ответы или дефолты)
    assert all(v is not None for v in profile.values())


def test_questionnaire_with_custom_fields(seeded_db):
    from app.models import CustomFormField

    seeded_db.add(CustomFormField(
        code='phone', label='Телефон', field_type='phone',
        required=True, sort_order=0, is_active=True,
    ))
    seeded_db.commit()

    engine = SurveyEngine(seeded_db)
    payload, _state = _run_flow(engine, stop_at_custom=True)

    assert payload is not None
    assert payload.get('is_custom')
    assert payload['fields'][0]['code'] == 'phone'


def test_recommender_without_model(seeded_db):
    recommender = Recommender(seeded_db)
    recs = recommender.get_recommendations({'software_development': 5.0})
    assert recs[0]['field'] == 'Модель не обучена'
    assert 'обуч' in recs[0]['explanation'].lower()


def test_match_level_thresholds():
    assert get_match_level(90) == 'IDEAL'
    assert get_match_level(75) == 'EXCELLENT'
    assert get_match_level(60) == 'GOOD'
    assert get_match_level(45) == 'AVERAGE'
    assert get_match_level(10) == 'LOW'


def test_session_model_roundtrip(seeded_db):
    from app.services.responses import get_session_by_uuid

    session = SurveySession(
        session_uuid='test_uuid_1',
        stage='screening',
        status='in_progress',
        state={'stage': 'screening', 'answers': {'x': 1}},
        source='cli',
    )
    seeded_db.add(session)
    seeded_db.commit()

    loaded = get_session_by_uuid(seeded_db, 'test_uuid_1')
    assert loaded is not None
    assert loaded.state['answers'] == {'x': 1}