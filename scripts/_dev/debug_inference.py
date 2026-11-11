"""Диагностика инференса: профиль vs сырые вероятности модели."""
import sys

sys.path.insert(0, '/app')

import numpy as np

from app.database import SessionLocal
from app.models import SurveySession
from app.services.recommender import Recommender
from app.services.feature_normalization import normalize_profile_values

STATE_SKILLS = {
    'ГОС': ['management', 'public_administration', 'legal_knowledge',
            'economic_analysis', 'social_research', 'communication_skill'],
    'ФИЗИКА': ['experimental_physics', 'nuclear_physics', 'aerospace_design',
               'power_engineering', 'electronics', 'automation_tech', 'math_modeling'],
}

db = SessionLocal()
try:
    rec = Recommender(db)
    run = rec.latest_run()
    model, scaler, mlb, cfg = rec._load(run)
    features = cfg['features']
    print('RUN:', run.id, '| temperature:', cfg.get('temperature'))
    print('features:', len(features), '| directions:', len(cfg['directions']))

    session = db.query(SurveySession).filter(
        SurveySession.status == 'completed',
        SurveySession.profile.isnot(None),
    ).order_by(SurveySession.id.desc()).first()
    profile = session.profile
    print('SESSION:', session.id)

    for group, skills in STATE_SKILLS.items():
        vals = {s: profile.get(s) for s in skills if s in features}
        print(f'{group}: {vals}')

    row = np.array([normalize_profile_values(profile, features)], dtype='float32')
    x = scaler.transform(row)
    raw = np.asarray(model.predict(x, verbose=0)[0], dtype='float64')
    t = float(cfg.get('temperature', 1.0) or 1.0)
    cal = np.power(np.clip(raw, 1e-9, 1.0), 1.0 / t) if t and abs(t - 1.0) > 1e-6 else raw

    names = mlb.classes_
    order = np.argsort(raw)[::-1]
    print('\nТоп-10 по сырым вероятностям (raw | calibrated):')
    for i in order[:10]:
        print(f'  {names[i][:60]:<60} raw={raw[i]:.4f} cal={cal[i]:.4f}')
finally:
    db.close()
