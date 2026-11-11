"""Смоук-тест: прогресс генерации синтетики и accuracy в метриках."""
import importlib.util
import sys

sys.path.insert(0, '/app')

spec = importlib.util.spec_from_file_location('trainer_new', '/tmp/trainer_new.py')
trainer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trainer)

# --- 1. Прогресс генерации ---
progress_log = []
features = ['ai_ml', 'software_development', 'ege_math', 'ege_russian', 'logical_thinking']
dirs = ['Направление А', 'Направление Б']
skill_map = {
    'Направление А': ['ai_ml', 'software_development', 'ege_math'],
    'Направление Б': ['software_development', 'ege_russian'],
}
df, labels = trainer.generate_training_data(
    features, dirs, skill_map,
    progress_callback=lambda pct, rows: progress_log.append((pct, rows)),
)
print('rows:', len(df), 'expected:', len(dirs) * 5000 + 5000)
pcts = [p for p, _ in progress_log]
assert len(df) == len(dirs) * 5000 + 5000
assert pcts == sorted(pcts), pcts
assert pcts[0] > 0 and pcts[-1] <= 95 and pcts[-1] >= 80, pcts
print('PROGRESS_OK: first=%s last=%s steps=%d' % (pcts[0], pcts[-1], len(pcts)))

# --- 2. Accuracy в метриках ---
import numpy as np
y_true = np.array([
    [1, 0, 1],
    [0, 1, 0],
    [1, 1, 0],
])
y_pred = np.array([
    [0.9, 0.1, 0.8],
    [0.2, 0.7, 0.1],
    [0.1, 0.9, 0.4],
])
m = trainer.compute_metrics(y_true, y_pred, ['A', 'B', 'C'])
print('accuracy:', m['accuracy'], 'subset_accuracy:', m['subset_accuracy'])
assert 'accuracy' in m and 'subset_accuracy' in m
assert 0 <= m['accuracy'] <= 1 and 0 <= m['subset_accuracy'] <= 1
print('METRICS_OK')
