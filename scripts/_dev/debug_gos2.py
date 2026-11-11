"""Метрики класса + предсказание на эталонном кластерном профиле."""
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
target = 'Прикладная информатика в управлении корпоративными системами'
ti = names.index(target)

m = run.metrics or {}
for d in m.get('per_direction', []):
    if d['label'] == target:
        print('TRAIN METRICS:', d)

# Эталонный кластерный профиль: все key навыки 4.8, остальные 3.0
skills = cfg['skills'][target]
profile = {f: 3.0 for f in features if not f.startswith('ege_')}
for f in features:
    if f.startswith('ege_'):
        profile[f] = 0
profile['desired_salary'] = 120000
for s in skills:
    profile[s] = 4.8
profile.update({'ege_russian': 80, 'ege_social': 90})

row = np.array([normalize_profile_values(profile, features)], dtype='float32')
raw = np.asarray(model.predict(scaler.transform(row), verbose=0)[0], dtype='float64')
order = np.argsort(raw)[::-1]
print(f'КЛАСТЕРНЫЙ профиль: {target} = {raw[ti]*100:.1f}% (место {int(np.where(order == ti)[0][0]) + 1})')
for i in order[:5]:
    print(f'   {raw[i]*100:5.1f}%  {names[i][:55]}')

# Мини-обучение на 500 строках одного этого класса для проверки данных:
# если модель не может выучить даже это — проблема в данных
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from app.services.trainer import generate_training_data

df, labels = generate_training_data(features, [target, 'Цифровые технологии в бизнесе'],
                                    {target: skills,
                                     'Цифровые технологии в бизнесе': cfg['skills']['Цифровые технологии в бизнесе']})
df = df[[c for c in df.columns if c != 'chosen_fields']]
X = df.values.astype('float32')
y = np.array([1 if l == [target] else 0 for l in labels])
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42)
lr = LogisticRegression(max_iter=2000).fit(Xtr, ytr)
print('LogReg различимость двух классов:', round(lr.score(Xte, yte), 3))
db.close()
