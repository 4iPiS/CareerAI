"""Смоук: добавление направления/признака в каталог отражается в синтетике
и не ломает рекомендатель (старая модель просто не знает новых направлений).

Сценарий:
1. Добавляем тестовое направление и признак (is_active=True).
2. load_config видит их; generate_training_data на коротком списке OK.
3. Рекомендатель на старой модели работает, не падает, новое направление
   отсутствует в рекомендациях (ожидаемо — до переобучения).
4. Удаляем тестовые объекты.
"""
import sys

sys.path.insert(0, '/app')

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Direction, Feature
from app.services.trainer import load_config, generate_training_data

db = SessionLocal()
try:
    # --- 1. Добавляем тестовые объекты каталога ---
    test_feature = Feature(
        code='_test_feature_x', label='Тестовый признак', data_type='rating_1_5',
        default_value=3, sort_order=999, is_common=True, is_active=True,
    )
    test_direction = Direction(
        name='_Тестовое направление', fgos_code='00.00.00', study_years=4,
        sort_order=999, is_active=True, description='Тест',
    )
    db.add(test_feature)
    db.add(test_direction)
    db.commit()
    db.refresh(test_direction)
    test_direction.features.append(test_feature)
    db.commit()
    fid, did = test_feature.id, test_direction.id
    print('Добавлены тестовые объекты:', fid, did)

    # --- 2. load_config видит их ---
    features, directions, skill_map = load_config(db)
    assert '_test_feature_x' in features, features[-5:]
    assert '_Тестовое направление' in directions
    assert '_test_feature_x' in skill_map['_Тестовое направление']
    print('load_config OK: признак и направление в конфигурации')

    # --- 3. Синтетика на коротком списке с новым направлением ---
    short_dirs = directions[-2:]
    df, labels = generate_training_data(
        [f for f in features if f in ('_test_feature_x', 'logical_thinking', 'desired_salary')] + short_dirs and
        ['_test_feature_x', 'logical_thinking', 'desired_salary'],
        ['_Тестовое направление'],
        {'_Тестовое направление': ['_test_feature_x']},
    )
    print('Синтетика с новым направлением OK, строк:', len(df))
    assert '_test_feature_x' in df.columns

    # --- 4. Рекомендатель со старой моделью не падает ---
    from app.services.recommender import Recommender
    rec = Recommender(db)
    if rec.latest_run():
        profile = {f: 3.5 for f in features if not f.startswith('ege_') and f != 'desired_salary'}
        profile['desired_salary'] = 100000
        for f in features:
            if f.startswith('ege_'):
                profile[f] = 0
        recs = rec.get_recommendations(profile, top_n=5)
        assert all(isinstance(r['probability'], int) for r in recs)
        assert '_Тестовое направление' not in [r['field'] for r in recs]
        print('Рекомендатель OK: не падает, новое направление до переобучения не в топе')

    # --- 5. Уборка ---
    d = db.get(Direction, did)
    if d:
        d.features.clear()
        db.delete(d)
    f = db.get(Feature, fid)
    if f:
        db.delete(f)
    db.commit()
    print('Тестовые объекты удалены. CATALOG_TEST_OK')
finally:
    db.close()
