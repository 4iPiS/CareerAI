"""Проверка: desired_salary в фичах модели и его эффект на предсказания."""
import sys

sys.path.insert(0, '/app')

import numpy as np

from app.database import SessionLocal
from app.models import SurveySession
from app.services.recommender import Recommender

db = SessionLocal()
try:
    rec = Recommender(db)
    run = rec.latest_run()
    model, scaler, mlb, cfg = rec._load(run)
    features = cfg['features']
    print('desired_salary in features:', 'desired_salary' in features)
    print('salary-подобные фичи:', [f for f in features if 'salary' in f.lower()])

    idx = features.index('desired_salary') if 'desired_salary' in features else None
    if idx is not None:
        print('scaler.mean_[salary] =', scaler.mean_[idx], '| scale =', scaler.scale_[idx])

    session = db.query(SurveySession).filter(
        SurveySession.status == 'completed',
        SurveySession.profile.isnot(None),
    ).order_by(SurveySession.id.desc()).first()
    profile = session.profile
    print('SESSION:', session.id, '| profile desired_salary =', profile.get('desired_salary'))
    print('profile salary-подобные:', {k: v for k, v in profile.items() if 'salary' in k.lower()})

    # Прогноз со «сломанным» salary=5.0 (клампится) и с честным значением
    row_broken, row_fixed = [], []
    for f in features:
        if f == 'desired_salary':
            row_broken.append(5.0)
            row_fixed.append(float(profile.get('desired_salary') or 100000))
        else:
            from app.services.feature_normalization import normalize_feature_value
            row_fixed.append(normalize_feature_value(f, profile.get(f)))
            v = profile.get(f)
            if v is None:
                v = 1.0 if f.startswith('ege_') else 0.0
            else:
                v = float(v)
                if f.startswith('ege_'):
                    v = max(1.0, min(5.0, (v / 100.0) * 4.0 + 1.0))
                else:
                    v = max(0.0, min(5.0, v))
            row_broken.append(v)

    names = mlb.classes_
    for label, row in (('SALARY=5.0 (клампнутый)', row_broken), ('SALARY=сырой', row_fixed)):
        x = scaler.transform(np.array([row], dtype='float32'))
        raw = np.asarray(model.predict(x, verbose=0)[0], dtype='float64')
        order = np.argsort(raw)[::-1]
        z = x[0][idx] if idx is not None else None
        print(f'\n{label} (z_salary={z:.1f}]):')
        for i in order[:5]:
            print(f'  {raw[i]*100:5.1f}%  {names[i][:60]}')
finally:
    db.close()
