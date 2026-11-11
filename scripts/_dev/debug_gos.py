"""Разбор гос-кейса: топ-10 и вероятности при разных вариациях профиля."""
import sys

sys.path.insert(0, '/app')

import numpy as np

from app.database import SessionLocal
from app.services.recommender import Recommender
from app.services.feature_normalization import normalize_profile_values

db = SessionLocal()
rec = Recommender(db)
run = rec.latest_run()
model, scaler, mlb, cfg = rec._load(run)
features = cfg['features']
names = list(mlb.classes_)
print('RUN:', run.id)

target = 'Прикладная информатика в управлении корпоративными системами'
print('skills направления:', cfg['skills'].get(target))

def show(profile, title):
    row = np.array([normalize_profile_values(profile, features)], dtype='float32')
    raw = np.asarray(model.predict(scaler.transform(row), verbose=0)[0], dtype='float64')
    order = np.argsort(raw)[::-1]
    ti = names.index(target)
    print(f'\n{title}: {target} = {raw[ti]*100:.1f}% (место {int(np.where(order == ti)[0][0]) + 1})')
    for i in order[:4]:
        print(f'   {raw[i]*100:5.1f}%  {names[i][:55]}')

base = {f: 3.0 for f in features if not f.startswith('ege_')}
for f in features:
    if f.startswith('ege_'):
        base[f] = 0
base['desired_salary'] = 120000
base.update({'ege_russian': 80, 'ege_social': 90, 'ege_history': 75})

p1 = dict(base)
p1.update({'public_administration': 5, 'management': 5, 'business_analytics': 4,
           'legal_knowledge': 3, 'economic_analysis': 4})
show(p1, 'Гос-профиль (legal=3, ba=4)')

p2 = dict(p1)
p2['legal_knowledge'] = 2
show(p2, 'Гос-профиль с legal=2')

p3 = dict(p1)
p3['business_analytics'] = 5
show(p3, 'Гос-профиль с ba=5')

p4 = dict(p1)
p4['legal_knowledge'] = 1
show(p4, 'Гос-профиль с legal=1')
db.close()
