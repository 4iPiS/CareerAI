"""Смоук-тест нормализации и структурного объяснения (запуск в контейнере)."""
import sys

sys.path.insert(0, '/tmp')
sys.path.insert(0, '/app')

import fn  # noqa: E402

assert fn.ege_to_scale(0) == 1.0
assert fn.ege_to_scale(100) == 5.0
assert abs(fn.ege_to_scale(50) - 3.0) < 1e-9
assert fn.normalize_feature_value('ege_math', None) == 1.0
assert fn.normalize_feature_value('ege_math', 80) == 4.2
assert fn.normalize_feature_value('software_development', 7) == 5.0
vals = fn.normalize_profile_values(
    {'ege_math': 100, 'software_development': 5, 'ai_ml': None},
    ['ege_math', 'software_development', 'ai_ml'],
)
assert vals == [5.0, 5.0, 0.0], vals
print('NORMALIZATION_OK', vals)

from app.services.recommender import Recommender  # noqa: E402

exp = Recommender._build_explanation(
    'Инженерия систем ИИ', 'ПОДХОДИТ',
    {
        'software_development': 5, 'ai_ml': 2.0, 'algorithms_theory': 3.5,
        'ege_informatics': 90, 'logical_thinking': 4.5,
    },
    ['software_development', 'ai_ml', 'algorithms_theory', 'ege_informatics'],
)
print('VERDICT:', exp['verdict'])
print('STRENGTHS:', exp['strengths'])
print('WEAKNESSES:', exp['weaknesses'])
print('ADVICE:', exp['advice'])
print('SUMMARY:', exp['summary'])
print('TEXT:', exp['text'])
assert exp['strengths'] and exp['weaknesses'] and exp['advice']
assert exp['summary'] and '|' in exp['text']
print('EXPLANATION_OK')
