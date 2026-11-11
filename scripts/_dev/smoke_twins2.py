"""Диагностика различимости двойников: accuracy по блокам данных."""
import sys

sys.path.insert(0, '/tmp')
sys.path.insert(0, '/app')

import importlib.util
import numpy as np

spec = importlib.util.spec_from_file_location('trainer_new', '/tmp/trainer_new.py')
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)

features = ['software_development', 'ai_ml', 'logical_thinking', 'desired_salary', 'ege_math', 'ege_russian']
A, B = 'Направление А (двойник)', 'Направление Б (двойник)'
skills = ['software_development', 'ai_ml']
skill_map = {A: list(skills), B: list(skills)}

df, labels = trainer.generate_training_data(features, [A, B], skill_map)
df = trainer.normalize_dataframe_ege(df, features)

# Статистика: средние key-навыки по направлениям (реалистичный блок = 3000 строк)
import pandas as pd
dA = df[(df['chosen_fields'].astype(str) == str([A]))]
dB = df[(df['chosen_fields'].astype(str) == str([B]))]
print('rows A(single):', len(dA), '| rows B(single):', len(dB))
print(f'  A: sd={dA["software_development"].mean():.2f} ai={dA["ai_ml"].mean():.2f}')
print(f'  B: sd={dB["software_development"].mean():.2f} ai={dB["ai_ml"].mean():.2f}')

X = df[[c for c in df.columns if c != 'chosen_fields']].values.astype('float32')
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.model_selection import train_test_split
mlb = MultiLabelBinarizer(classes=[A, B])
y = mlb.fit_transform(labels)
scaler = StandardScaler()
Xs = scaler.fit_transform(X)
Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, random_state=42)

# Доля «общих» строк (оба лейбла) в тесте
both = (yte[:, 0] == 1) & (yte[:, 1] == 1)
print(f'тест: всего={len(yte)}, с обоими лейблами={both.sum()} ({both.mean():.0%})')

model = trainer.build_model(Xs.shape[1], 2)
model.fit(Xtr, ytr, validation_split=0.2, epochs=40, batch_size=64, verbose=0)

pred = model.predict(Xte, verbose=0)
correct = (pred[:, 0] > pred[:, 1]) == (yte[:, 0] > yte[:, 1])
print(f'общая top-1 accuracy: {correct.mean():.3f}')
if both.sum() > 0:
    print(f'  на общих строках (обе метки): {correct[both].mean():.3f} (потолок ~0.5)')
    print(f'  на одинарных строках:        {correct[~both].mean():.3f}')
