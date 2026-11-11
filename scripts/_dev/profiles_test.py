"""Тест «профиль каждой области -> ожидаемое направление в топе».

Плюс: статус последних ранов обучения.
"""
import sys

sys.path.insert(0, '/app')

from app.database import SessionLocal
from app.models import ModelRun
from app.services.recommender import Recommender

# Область -> (ключевые навыки (код: балл), предметы ЕГЭ (код: балл 0-100))
AREA_PROFILES = {
    'IT/программирование': {
        'skills': {'software_development': 5, 'algorithms_theory': 5, 'ai_ml': 5,
                   'computer_systems': 4, 'logical_thinking': 5, 'problem_solving': 4},
        'ege': {'ege_math': 85, 'ege_informatics': 90, 'ege_russian': 75},
    },
    'Физика': {
        'skills': {'experimental_physics': 5, 'nuclear_physics': 5, 'math_modeling': 5,
                   'logical_thinking': 5},
        'ege': {'ege_math': 85, 'ege_physics': 90, 'ege_russian': 75},
    },
    'Право': {
        'skills': {'legal_knowledge': 5, 'communication_skill': 4, 'social_research': 4,
                   'public_administration': 4},
        'ege': {'ege_russian': 80, 'ege_social': 90, 'ege_history': 80},
    },
    'Психология': {
        'skills': {'psychological_counseling': 5, 'communication_skill': 5,
                   'social_research': 4, 'memory_ability': 4},
        'ege': {'ege_russian': 80, 'ege_biology': 85, 'ege_social': 80},
    },
    'Лингвистика/перевод': {
        'skills': {'linguistics_skill': 5, 'communication_skill': 5},
        'ege': {'ege_russian': 85, 'ege_foreign': 90, 'ege_literature': 80},
    },
    'Бизнес/маркетинг': {
        'skills': {'business_analytics': 5, 'economic_analysis': 5, 'management': 4,
                   'communication_skill': 4},
        'ege': {'ege_russian': 75, 'ege_math': 70, 'ege_social': 85},
    },
    'Химия/биотех': {
        'skills': {'chemical_analysis': 5, 'biotech': 5, 'experimental_physics': 3},
        'ege': {'ege_chemistry': 90, 'ege_biology': 85, 'ege_russian': 75},
    },
    'Экология/геология': {
        'skills': {'ecology': 5, 'geology': 5, 'chemical_analysis': 4},
        'ege': {'ege_geography': 90, 'ege_biology': 80, 'ege_russian': 75},
    },
    'Гос-управление (legal=3)': {
        'skills': {'public_administration': 5, 'management': 5, 'business_analytics': 4,
                   'legal_knowledge': 3, 'economic_analysis': 4},
        'ege': {'ege_russian': 80, 'ege_social': 90, 'ege_history': 75},
    },
    'Гос-управление (legal=2)': {
        'skills': {'public_administration': 5, 'management': 5, 'business_analytics': 4,
                   'legal_knowledge': 2, 'economic_analysis': 4},
        'ege': {'ege_russian': 80, 'ege_social': 90, 'ege_history': 75},
    },
    'Дизайн/IT-креатив': {
        'skills': {'design': 5, 'software_development': 4, 'communication_skill': 4},
        'ege': {'ege_russian': 80, 'ege_literature': 85, 'ege_informatics': 75},
    },
}

# Ожидаемые ключевые слова в названии направления топ-1/топ-3
AREA_EXPECT = {
    'IT/программирование': ['программного обеспечения', 'информационных систем', 'искусственного интеллекта', 'данных'],
    'Физика': ['физика', 'физик', 'микромира', 'ядра'],
    'Право': ['правов'],
    'Психология': ['психолог'],
    'Лингвистика/перевод': ['перевод', 'межкультурная'],
    'Бизнес/маркетинг': ['бизнес', 'маркетингов'],
    'Химия/биотех': ['химия', 'биолог', 'биотех', 'нано'],
    'Экология/геология': ['эколог', 'геолог', 'геофиз', 'геоаналит'],
    'Гос-управление (legal=3)': ['управлении корпоративн', 'государствен', 'управлен', 'цифровые технологии'],
    'Гос-управление (legal=2)': ['управлении корпоративн', 'государствен', 'управлен', 'цифровые технологии'],
    'Дизайн/IT-креатив': ['дизайн'],
}


def main():
    db = SessionLocal()
    rec = Recommender(db)
    run = rec.latest_run()
    print('LATEST_RUN:', run.id if run else None)

    runs = db.query(ModelRun).order_by(ModelRun.id.desc()).limit(3).all()
    for r in runs:
        m = r.metrics or {}
        print(f'RUN {r.id}: {r.status.value}, epochs {r.current_epoch}/{r.total_epochs}, '
              f'acc={m.get("accuracy")}, top1={m.get("top1_accuracy")}')

    if run is None:
        print('NO_MODEL')
        return

    model, scaler, mlb, cfg = rec._load(run)
    features = cfg['features']
    names = list(mlb.classes_)

    import numpy as np
    from app.services.feature_normalization import normalize_profile_values

    passed, failed = 0, 0
    for area, spec in AREA_PROFILES.items():
        profile = {}
        for f in features:
            if f.startswith('ege_'):
                profile[f] = spec['ege'].get(f, 0)
            elif f == 'desired_salary':
                profile[f] = 120000
            elif f in spec['skills']:
                profile[f] = float(spec['skills'][f])
            else:
                # Нерелевантные навыки: реалистичный средний уровень
                # (в опросе не выбранные области получают 2-4)
                profile[f] = 3.0
        row = np.array([normalize_profile_values(profile, features)], dtype='float32')
        raw = np.asarray(model.predict(scaler.transform(row), verbose=0)[0], dtype='float64')
        order = np.argsort(raw)[::-1]
        top3 = [names[i] for i in order[:3]]
        expect = AREA_EXPECT[area]
        hit = any(any(kw in t.lower() for kw in expect) for t in top3)
        status = 'OK ' if hit else 'FAIL'
        if hit:
            passed += 1
        else:
            failed += 1
        print(f'[{status}] {area}: ' + ' | '.join(
            f'{names[i][:38]} ({raw[i]*100:.1f}%)' for i in order[:3]))
    print(f'RESULT: {passed} OK, {failed} FAIL из {len(AREA_PROFILES)}')
    db.close()


if __name__ == '__main__':
    main()
