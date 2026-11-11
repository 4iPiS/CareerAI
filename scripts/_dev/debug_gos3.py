"""Критический тест: модель на родных сэмплах синтетики класса управления.

Если на сэмплах из обучающего распределения класс тоже 0% —
инференс-пайплайн расходится с обучением (нормализация/порядок признаков).
"""
import sys

sys.path.insert(0, '/app')

import importlib.util
import numpy as np

from app.database import SessionLocal
from app.services.recommender import Recommender
from app.services.feature_normalization import normalize_profile_values

spec = importlib.util.spec_from_file_location('trainer_new', '/app/app/services/trainer.py')
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)

db = SessionLocal()
rec = Recommender(db)
run = rec.latest_run()
model, scaler, mlb, cfg = rec._load(run)
features = cfg['features']
names = list(mlb.classes_)
target = 'Прикладная информатика в управлении корпоративными системами'
ti = names.index(target)
print('RUN:', run.id)
print('features (порядок):', features[:8], '...')

# 1) Родные сэмплы синтетики этого класса
df, labels = trainer.generate_training_data(
    features, [target], {target: cfg['skills'][target]},
)
df = trainer.normalize_dataframe_ege(df, features)
sample = df.iloc[0].to_dict()
row = np.array([normalize_profile_values(sample, features)], dtype='float32')
raw = np.asarray(model.predict(scaler.transform(row), verbose=0)[0], dtype='float64')
print(f'СЭМПЛ СИНТЕТИКИ: {target} = {raw[ti]*100:.2f}%')
order = np.argsort(raw)[::-1]
for i in order[:3]:
    print(f'   {raw[i]*100:5.1f}%  {names[i][:55]}')

# 2) Сравнение порядка признаков: X в обучении vs cfg['features']
# Воссоздаём как в run_training:
feature_cols = [c for c in df.columns if c != 'chosen_fields']
print('feature_cols == cfg features:', feature_cols == features)

# 3) Сырой профиль без normalize_profile_values (как строился X в обучении):
row2 = np.array([[float(sample.get(c, 0) or 0) for c in features]], dtype='float32')
raw2 = np.asarray(model.predict(scaler.transform(row2), verbose=0)[0], dtype='float64')
print(f'СЭМПЛ (прямой порядок features): {target} = {raw2[ti]*100:.2f}%')
db.close()
