"""Комплексная проверка проекта: импорт приложения, API, состояние БД, раны."""
import sys
import traceback

sys.path.insert(0, '/app')

results = []


def check(name, fn):
    try:
        fn()
        results.append(('OK ', name))
    except Exception as e:
        results.append(('FAIL', f'{name}: {e!r}'))
        traceback.print_exc()


# --- 1. Импорт всех модулей приложения ---
def _imports():
    import importlib
    mods = [
        'app.main', 'app.config', 'app.database',
        'app.services.feature_normalization', 'app.services.trainer',
        'app.services.recommender', 'app.services.api_recommender',
        'app.services.unified_recommender', 'app.services.questionnaire',
        'app.services.responses', 'app.services.security', 'app.services.media',
        'app.api.public', 'app.api.admin_auth', 'app.api.admin_catalog',
        'app.api.admin_train', 'app.api.admin_stats', 'app.api.admin_settings',
        'app.api.admin_recommender', 'app.api.admin_users', 'app.api.admin_media',
        'app.api.admin_custom', 'app.api.admin_questions',
        'app.models',
    ]
    for m in mods:
        importlib.import_module(m)


check('Импорт всех модулей', _imports)

# --- 2. Создание приложения и роуты ---
def _app():
    from app.main import app
    schema = app.openapi()
    paths = set(schema.get('paths', {}))
    for required in ('/api/v1/start', '/api/v1/answer', '/api/v1/feedback',
                     '/api/v1/directions', '/api/v1/settings',
                     '/api/admin/train/status', '/api/admin/auth/login'):
        assert required in paths, f'нет роута {required} (есть: {sorted(paths)[:8]}…)'
    print(f'   Роутов в OpenAPI: {len(paths)}')


check('Приложение и роуты', _app)

# --- 3. API через TestClient ---
def _api():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    r = client.get('/api/v1/directions')
    assert r.status_code == 200
    dirs = r.json()['directions']
    assert len(dirs) >= 30, len(dirs)
    r = client.get('/api/v1/settings')
    assert r.status_code == 200
    # старт опроса
    r = client.post('/api/v1/start')
    assert r.status_code == 200, r.text
    sid = r.json()['session_id']
    assert sid
    # админ без токена — 401
    r = client.get('/api/admin/train/status')
    assert r.status_code in (401, 403), r.status_code
    print(f'   API OK: {len(dirs)} направлений, сессия {sid[:8]}…')


check('API (health/directions/settings/start/auth)', _api)

# --- 4. БД: раны, зависшие процессы ---
def _db():
    from app.database import SessionLocal
    from app.models import ModelRun, ModelRunStatus, SurveySession, Direction, Feature
    db = SessionLocal()
    stuck = db.query(ModelRun).filter(
        ModelRun.status.in_([ModelRunStatus.running, ModelRunStatus.pending]),
    ).count()
    assert stuck == 0, f'зависших ранов: {stuck}'
    n_dirs = db.query(Direction).filter(Direction.is_active).count()
    n_feats = db.query(Feature).filter(Feature.is_active).count()
    n_sessions = db.query(SurveySession).count()
    print(f'   БД: направлений {n_dirs}, признаков {n_feats}, сессий {n_sessions}, зависших ранов 0')
    db.close()


check('БД (нет зависших ранов, каталог цел)', _db)

# --- 5. Каталог: согласованность ---
def _catalog():
    from app.services.trainer import load_config
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Direction
    db = SessionLocal()
    features, directions, skill_map = load_config(db)
    assert len(features) > 20 and len(directions) > 25
    # каждое направление имеет хотя бы один key-навык
    empty = [d for d in directions if not skill_map.get(d)]
    assert not empty, f'направления без key-навыков: {empty}'
    # все key-навыки существуют в признаках
    fset = set(features)
    bad = [(d, s) for d in directions for s in skill_map[d] if s not in fset]
    assert not bad, f'несуществующие key-навыки: {bad[:5]}'
    print(f'   Каталог: {len(directions)} направлений, {len(features)} признаков, без пустых')
    db.close()


check('Каталог (key-навыки согласованы)', _catalog)

# --- 6. Рекомендатель: E2E на реальной сессии ---
def _rec():
    from app.database import SessionLocal
    from app.models import SurveySession
    from app.services.recommender import Recommender
    db = SessionLocal()
    rec = Recommender(db)
    run = rec.latest_run()
    assert run is not None and run.status.value == 'completed'
    model, scaler, mlb, cfg = rec._load(run)
    s = db.query(SurveySession).filter(
        SurveySession.status == 'completed', SurveySession.profile.isnot(None),
    ).order_by(SurveySession.id.desc()).first()
    recs = rec.get_recommendations(s.profile, top_n=5)
    assert len(recs) == 5
    probs = [r['probability'] for r in recs]
    assert all(isinstance(p, int) and 0 <= p <= 100 for p in probs)
    assert probs == sorted(probs, reverse=True)
    assert all(r['explanation'] and r['verdict'] for r in recs)
    print(f'   Рекомендатель OK (run {run.id}, top-1 {probs[0]}%)')
    db.close()


check('Рекомендатель E2E', _rec)

print()
fails = [r for r in results if r[0] == 'FAIL']
for status, name in results:
    print(f'[{status}] {name}')
print(f'\nИТОГО: {len(results) - len(fails)} OK, {len(fails)} FAIL')
sys.exit(1 if fails else 0)
