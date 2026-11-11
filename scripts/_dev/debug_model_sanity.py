"""Проверка адекватности модели: синтетический идеальный профиль vs реальный."""
import sys

sys.path.insert(0, '/app')

import numpy as np

from app.database import SessionLocal
from app.models import SurveySession
from app.services.recommender import Recommender
from app.services.feature_normalization import normalize_profile_values

db = SessionLocal()
try:
    rec = Recommender(db)
    run = rec.latest_run()
    model, scaler, mlb, cfg = rec._load(run)
    features = cfg['features']
    names = list(mlb.classes_)
    skill_map = cfg.get('skills', {})
    print('RUN:', run.id)

    def predict_top(profile, k=6, title=''):
        row = np.array([normalize_profile_values(profile, features)], dtype='float32')
        raw = np.asarray(model.predict(scaler.transform(row), verbose=0)[0], dtype='float64')
        order = np.argsort(raw)[::-1]
        print(f'\n{title}')
        for i in order[:k]:
            print(f'  {raw[i]*100:5.1f}%  {names[i][:60]}')
        # где правильный ответ
        return raw

    # 1) Полный профиль последней сессии
    s = db.query(SurveySession).filter(
        SurveySession.status == 'completed',
        SurveySession.profile.isnot(None),
    ).order_by(SurveySession.id.desc()).first()
    print('SESSION:', s.id)
    print('PROFILE:', {k: v for k, v in sorted(s.profile.items()) if k != 'desired_salary'})
    predict_top(s.profile, title='=== Последняя сессия ===')

    # 2) Идеальный профиль программиста
    prog = {}
    for f in features:
        if f.startswith('ege_'):
            prog[f] = {'ege_math': 90, 'ege_informatics': 90, 'ege_russian': 80}.get(f, 0)
        elif f == 'desired_salary':
            prog[f] = 150000
        else:
            prog[f] = 1.0
    for f in ['software_development', 'ai_ml', 'algorithms_theory', 'computer_systems']:
        if f in prog:
            prog[f] = 5.0
    for f in ['cybersecurity', 'business_analytics']:
        if f in prog:
            prog[f] = 4.0
    predict_top(prog, title='=== Идеальный программист (синтетический) ===')

    # 3) Профиль, сгенерированный самим тренером для «Технологии разработки ПО»
    from app.services.trainer import generate_training_data
    target_dir = None
    for n in names:
        if 'программного обеспечения' in n:
            target_dir = n
            break
    if target_dir:
        feats, dirs, smap = features, [n for n in names], skill_map
        df, labels = generate_training_data(feats, [target_dir], {target_dir: smap.get(target_dir, [])})
        sample = df.iloc[0].to_dict()
        raw = predict_top(sample, title=f'=== Синтетика тренера для «{target_dir}» ===')
        ti = names.index(target_dir)
        print(f'  >>> prob для «{target_dir}»: {raw[ti]*100:.1f}%')
finally:
    db.close()
