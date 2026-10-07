"""Интеграционные тесты API платформы (админ-аутентификация и публичный API)."""

from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app


def _override_db(seeded_db):
    def _get_db():
        yield seeded_db
    app.dependency_overrides[get_db] = _get_db
    return TestClient(app)


def test_admin_unauthorized(seeded_db):
    client = _override_db(seeded_db)
    assert client.get('/api/admin/stats').status_code == 401
    app.dependency_overrides.clear()


def test_admin_login_and_access(seeded_db):
    client = _override_db(seeded_db)
    resp = client.post('/api/admin/auth/login', json={
        'username': 'admin',
        'password': 'admin123',
    })
    assert resp.status_code == 200
    assert client.get('/api/admin/stats').status_code == 200
    me = client.get('/api/admin/auth/me')
    assert me.status_code == 200
    assert me.json()['role'] == 'admin'
    app.dependency_overrides.clear()


def test_admin_bad_login(seeded_db):
    client = _override_db(seeded_db)
    resp = client.post('/api/admin/auth/login', json={
        'username': 'admin',
        'password': 'wrong-password',
    })
    assert resp.status_code == 401
    app.dependency_overrides.clear()


def test_public_start_and_directions(seeded_db):
    client = _override_db(seeded_db)
    start = client.post('/api/v1/start')
    assert start.status_code == 200
    data = start.json()
    assert data['session_id']
    assert data['question']['id']

    directions = client.get('/api/v1/directions')
    assert directions.status_code == 200
    # 31 активная программа (профили) после полного пайплайна сида
    assert len(directions.json()['directions']) == 31

    settings = client.get('/api/v1/settings')
    assert settings.status_code == 200
    assert settings.json()['settings']['university_name']
    app.dependency_overrides.clear()


def test_public_answer_flow(seeded_db):
    client = _override_db(seeded_db)
    start = client.post('/api/v1/start').json()
    session_id = start['session_id']
    qid = start['question']['id']

    for _ in range(250):
        resp = client.post('/api/v1/answer', json={
            'session_id': session_id,
            'question_id': qid,
            'answer': 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        if data['done']:
            assert data['recommendations']
            break
        qid = data['question']['id']

    assert data['done']
    app.dependency_overrides.clear()


def test_public_feedback(seeded_db):
    client = _override_db(seeded_db)
    start = client.post('/api/v1/start').json()
    resp = client.post('/api/v1/feedback', json={
        'session_id': start['session_id'],
        'chosen_fields': ['Программная инженерия'],
        'feedback_score': 4,
    })
    assert resp.status_code == 200
    app.dependency_overrides.clear()