"""Смоук-тест: различимость «двойников» (одинаковые навыки) после emphasis-фикса."""
import sys

sys.path.insert(0, '/tmp')
sys.path.insert(0, '/app')

import importlib.util
import numpy as np

spec = importlib.util.spec_from_file_location('trainer_new', '/tmp/trainer_new.py')
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)

import fn  # noqa: E402
assert fn.normalize_feature_value('desired_salary', 150000) == 150000.0
assert fn.normalize_feature_value('desired_salary', None) == 100000.0
assert fn.normalize_feature_value('software_development', 7) == 5.0
print('SALARY_NORMALIZATION_OK')

features = ['software_development', 'ai_ml', 'logical_thinking', 'desired_salary', 'ege_math', 'ege_russian']
A, B = 'Направление А (двойник)', 'Направление Б (двойник)'
skills = ['software_development', 'ai_ml']
skill_map = {A: list(skills), B: list(skills)}  # ОДИНАКОВЫЕ навыки!

progress = []
df, labels = trainer.generate_training_data(
    features, [A, B], skill_map,
    progress_callback=lambda pct, rows: progress.append(pct),
)
print('rows:', len(df), '| progress:', progress[0], '->', progress[-1])
assert progress == sorted(progress)
assert progress[-1] <= 95

# Единая нормализация ЕГЭ, как в обучении
df = trainer.normalize_dataframe_ege(df, features)

X = df[[c for c in df.columns if c != 'chosen_fields']].values.astype('float32')
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from sklearn.model_selection import train_test_split
mlb = MultiLabelBinarizer(classes=[A, B])
y = mlb.fit_transform(labels)
scaler = StandardScaler()
Xs = scaler.fit_transform(X)
Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, random_state=42)

model = trainer.build_model(Xs.shape[1], 2)
model.fit(Xtr, ytr, validation_split=0.2, epochs=15, batch_size=64, verbose=0)

pred = model.predict(Xte, verbose=0)
acc_a = float(np.mean((pred[:, 0] > pred[:, 1]) == (yte[:, 0] > yte[:, 1])))
print(f'Различимость двойников (top-1 accuracy): {acc_a:.3f}')
assert acc_a > 0.85, acc_a
print('TWINS_OK')
