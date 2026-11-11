"""E2E: локальный рекоммендер на реальном профиле из БД (запуск в контейнере)."""
import sys

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import SurveySession
from app.services.recommender import Recommender

db = SessionLocal()
try:
    session = db.query(SurveySession).filter(SurveySession.profile.isnot(None)).order_by(
        SurveySession.id.desc()
    ).first()
    if session is None:
        print('NO_SESSION_WITH_PROFILE')
        sys.exit(0)

    profile = session.profile
    print('PROFILE keys:', sorted(profile.keys())[:10], '...')

    rec = Recommender(db)
    run = rec.latest_run()
    if run is None:
        print('NO_TRAINED_MODEL')
        sys.exit(0)
    print('RUN:', run.id, 'status:', run.status)

    recommendations = rec.get_recommendations(profile, top_n=5)
    for r in recommendations:
        print(f"{r['rank']}. {r['field']} — {r['probability']}% "
              f"(raw={r.get('raw_probability')}, {r['match_level']}, {r['verdict']})")
        print(f"   strengths: {r['strengths']}")
        print(f"   weaknesses: {r['weaknesses']}")
        print(f"   advice: {r['advice']}")

    # Проверки формата
    for r in recommendations:
        assert isinstance(r['probability'], int) and 0 <= r['probability'] <= 100, r['probability']
        assert r['match_level'] != 'LOW' or r['probability'] < 40
        assert isinstance(r['strengths'], list) and isinstance(r['weaknesses'], list)
    # Проценты не возрастают сверху вниз
    probs = [r['probability'] for r in recommendations]
    assert probs == sorted(probs, reverse=True), probs
    print('E2E_OK', probs)
finally:
    db.close()
