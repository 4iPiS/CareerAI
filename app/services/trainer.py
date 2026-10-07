"""Сервис обучения: динамический тренировщик на конфигурации из БД.

Признаки, направления и ключевые навыки читаются из PostgreSQL.
Артефакты сохраняются в {models_dir}/run_{id}/ (модель, scaler, mlb,
config.json). Каждый запуск — отдельная строка model_runs, что позволяет
хранить несколько версий модели и не ломать работающую.

Тяжёлые ML-зависимости (numpy, pandas, tensorflow, sklearn) импортируются
лениво — внутри функций, поэтому модуль можно импортировать без них.
"""

import json
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Direction, Feature, ModelRun, ModelRunStatus


def _clean_nan(obj: Any) -> Any:
    """Рекурсивно заменяет NaN/Inf на None для валидного JSON."""
    import numpy as np

    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, np.floating):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return _clean_nan(obj.tolist())
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nan(item) for item in obj]
    return obj

SALARY_CHOICES = [60000, 80000, 100000, 120000, 150000, 200000, 300000]

# Признак → предметы ЕГЭ, которые его усиливают (для синтетики)
EGE_SUBJECTS = [
    'ege_math', 'ege_russian', 'ege_informatics', 'ege_physics',
    'ege_chemistry', 'ege_biology', 'ege_social', 'ege_history',
    'ege_foreign', 'ege_literature', 'ege_geography',
]

EGE_BOOSTS = {
    'ege_math': [
        'math_modeling', 'algorithms_theory', 'computer_systems',
        'software_development', 'business_analytics', 'it_infrastructure',
        'power_engineering', 'automation_tech', 'electronics',
        'economic_analysis', 'ai_ml', 'cybersecurity',
    ],
    'ege_russian': [
        'communication_skill', 'legal_knowledge', 'social_research',
        'psychological_counseling', 'linguistics_skill', 'management',
        'public_administration', 'design',
    ],
    'ege_informatics': [
        'computer_systems', 'software_development', 'it_infrastructure',
        'algorithms_theory', 'automation_tech', 'business_analytics',
        'ai_ml', 'cybersecurity',
    ],
    'ege_physics': [
        'experimental_physics', 'nuclear_physics', 'power_engineering',
        'electronics', 'aerospace_design', 'automation_tech',
        'chemical_analysis', 'geology',
    ],
    'ege_chemistry': ['chemical_analysis', 'biotech'],
    'ege_biology': ['ecology', 'psychological_counseling', 'biotech'],
    'ege_social': [
        'management', 'public_administration', 'economic_analysis',
        'legal_knowledge', 'social_research', 'psychological_counseling',
    ],
    'ege_history': ['legal_knowledge', 'social_research', 'public_administration'],
    'ege_foreign': ['linguistics_skill'],
    'ege_literature': ['linguistics_skill', 'social_research', 'design'],
    'ege_geography': ['ecology', 'public_administration', 'geology'],
}


def _fill_ege(
    profile: dict,
    labels: list[str],
    skill_map: dict[str, list[str]],
    all_high: bool = False,
) -> None:
    """3-4 сданных ЕГЭ (релевантные + обязательные), остальные = -1.
    
    Закономерный -1: профильные предметы ВСЕГДА сданы, остальные ВСЕГДА -1.
    Это позволяет модели выучить связи «предмет → направление».
    """
    import numpy as np

    if not any(code.startswith('ege_') for code in profile):
        return

    boosted_skills = set()
    for label in labels:
        boosted_skills.update(skill_map.get(label, []))

    # Профильные предметы (релевантные навыкам направления)
    relevant = [
        s for s in EGE_SUBJECTS
        if any(sk in EGE_BOOSTS.get(s, []) for sk in boosted_skills)
    ]

    # Обязательные предметы
    mandatory = ['ege_russian']
    if 'ege_math' in profile:
        mandatory.append('ege_math')

    # Сданные = профильные + обязательные
    taken = list(set(relevant + mandatory))

    # ВСЕ несданные = -1
    for subject in EGE_SUBJECTS:
        if subject in profile and subject not in taken:
            profile[subject] = -1

    # Сданные = баллы
    for subject in taken:
        if subject not in profile:
            continue
        if all_high:
            score = float(np.random.uniform(88, 100))
        else:
            if subject in relevant:
                score = float(np.random.normal(72, 8))
            else:
                score = float(np.random.normal(65, 8))
            score = max(40, min(100, score))
        profile[subject] = int(round(score))


def set_seed(seed: int = 42) -> None:
    import numpy as np
    import tensorflow as tf

    np.random.seed(seed)
    tf.random.set_seed(seed)
    random.seed(seed)





def load_config(db: Optional[Session] = None) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """Активные признаки, направления и карта «направление → навыки»."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        features = db.scalars(
            select(Feature).where(Feature.is_active).order_by(Feature.sort_order),
        ).all()
        directions = db.scalars(
            select(Direction).where(Direction.is_active).order_by(Direction.sort_order),
        ).all()

        feature_codes = [f.code for f in features]
        direction_names = [d.name for d in directions]
        skill_map: dict[str, list[str]] = {}
        for d in directions:
            skill_map[d.name] = [f.code for f in d.features]

        return feature_codes, direction_names, skill_map
    finally:
        if close_db:
            db.close()


def generate_training_data(
    feature_codes: list[str],
    direction_names: list[str],
    skill_map: dict[str, list[str]],
    progress_callback=None,
) -> tuple['object', list[list[str]]]:
    """Синтетические данные по правилам «навык → направление».

    Возвращает (DataFrame, multi_labels). DataFrame импортируется лениво.
    """
    import numpy as np
    import pandas as pd

    data = []
    multi_labels = []
    
    # общее количество строк для расчёта прогресса
    n_dirs = len(direction_names) or 1
    _total_est = 500 * n_dirs + 2000 * n_dirs + 500 * n_dirs + 10000 + 5000 + 2000 * n_dirs + 500 * n_dirs + 15000 + 20000 + 1000 * n_dirs + 1000 * n_dirs + 1000 * n_dirs + 15000

    def add(profile: dict, labels: list[str], all_high: bool = False):
        profile['desired_salary'] = float(np.random.choice(SALARY_CHOICES))
        _fill_ege(profile, labels, skill_map, all_high=all_high)
        profile['chosen_fields'] = labels
        data.append(profile)
        multi_labels.append(labels)

    # 1b) УНИВЕРСАЛЬНЫЕ ОТЛИЧНИКИ — все 5, привязка к конкретным направлениям
    dirs = direction_names
    for di, direction in enumerate(dirs):
        key_skills = skill_map.get(direction, [])
        for _ in range(500):
            profile = {f: 5.0 for f in feature_codes}
            for ege_col in EGE_SUBJECTS:
                if ege_col in feature_codes and any(
                    s in EGE_BOOSTS.get(ege_col, []) for s in key_skills
                ):
                    profile[ege_col] = int(np.random.uniform(95, 100))
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(2, len(data))

    # 1c) ЧАСТИЧНО ИДЕАЛЬНЫЙ ПРОФИЛЬ — 2-3 ключевых = 5, остальные = 2-3.5
    for di, direction in enumerate(direction_names):
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {}
            for f in feature_codes:
                if f in key_skills:
                    profile[f] = 5.0
                else:
                    profile[f] = float(np.random.uniform(2.0, 3.5))
            for ege_col in EGE_SUBJECTS:
                if ege_col in feature_codes:
                    if any(s in EGE_BOOSTS.get(ege_col, []) for s in key_skills):
                        profile[ege_col] = int(np.random.uniform(75, 95))
                    else:
                        profile[ege_col] = -1
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(2, len(data))

    # 1d) СРЕДНИЙ ПРОФИЛЬ — все = 3-4, ЕГЭ = 60-75 (только у 40%)
    for i in range(10000):
        profile = {f: float(np.random.uniform(3.0, 4.0)) for f in feature_codes}
        for ege_col in EGE_SUBJECTS:
            if ege_col in feature_codes:
                if np.random.random() < 0.4:
                    profile[ege_col] = int(np.random.uniform(60, 75))
                else:
                    profile[ege_col] = -1
        # направления по навыкам
        scores = {}
        for direction, key_skills in skill_map.items():
            if not key_skills:
                continue
            avg = float(np.mean([profile[s] for s in key_skills]))
            scores[direction] = avg
        chosen = sorted(scores, key=scores.get, reverse=True)[:2]
        add(profile, chosen)
        if progress_callback and i % 2000 == 0:
            progress_callback(2, len(data))

    # 1e) БЕЗ ЕГЭ — только навыки, ЕГЭ все = -1
    for i in range(5000):
        profile = {f: float(np.random.uniform(2.0, 5.0)) for f in feature_codes}
        for ege_col in EGE_SUBJECTS:
            if ege_col in feature_codes:
                profile[ege_col] = -1
        scores = {}
        for direction, key_skills in skill_map.items():
            if not key_skills:
                continue
            avg = float(np.mean([profile[s] for s in key_skills]))
            if avg >= 3.0:
                scores[direction] = avg
        if scores:
            chosen = sorted(scores, key=scores.get, reverse=True)[:2]
        else:
            chosen = list(np.random.choice(direction_names, size=2, replace=False))
        add(profile, chosen)
        if progress_callback and i % 1000 == 0:
            progress_callback(2, len(data))

    # 2) чистые профили по одному направлению — сильный контраст
    dirs2 = direction_names
    for di, direction in enumerate(dirs2):
        key_skills = skill_map.get(direction, [])
        for _ in range(2000):
            profile = {
                f: 5.0 if f in key_skills else 1.0
                for f in feature_codes
            }
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(3, len(data))

    # 2b) усиленные чистые профили — высокие ЕГЭ по профильным предметам
    dirs2b = direction_names
    for di, direction in enumerate(dirs2b):
        key_skills = skill_map.get(direction, [])
        for _ in range(500):
            profile = {
                f: 5.0 if f in key_skills else 1.5
                for f in feature_codes
            }
            for ege_col in EGE_SUBJECTS:
                if ege_col in feature_codes and any(
                    s in EGE_BOOSTS.get(ege_col, []) for s in key_skills
                ):
                    profile[ege_col] = int(np.random.uniform(80, 98))
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(4, len(data))

    # 3) мультинаправленные профили — 2-3 направления, чёткий контраст
    for i in range(15000):
        profile = {f: 1.0 for f in feature_codes}
        num_dirs = int(np.random.choice([2, 3]))
        selected = list(
            np.random.choice(direction_names, size=num_dirs, replace=False),
        )
        for direction in selected:
            for skill in skill_map.get(direction, []):
                profile[skill] = 5.0
        for trait in ('logical_thinking', 'memory_ability', 'problem_solving'):
            if trait in profile:
                profile[trait] = float(np.random.uniform(3.5, 4.5))
        add(profile, selected)
        if progress_callback and i % 3000 == 0:
            progress_callback(5, len(data))

    # 4) шумные профили — низкий фон, случайные пики
    for i in range(20000):
        profile = {
            f: float(np.random.uniform(1.0, 2.5))
            for f in feature_codes
        }
        # случайные пики до 4.5 на 2-4 признака
        for _ in range(np.random.randint(2, 5)):
            f = np.random.choice(feature_codes)
            profile[f] = float(np.random.uniform(3.5, 4.5))
        scores = {}
        for direction, key_skills in skill_map.items():
            if not key_skills:
                continue
            avg = float(np.mean([profile[s] for s in key_skills]))
            if avg >= 3.0:
                scores[direction] = avg
        if not scores:
            chosen = list(
                np.random.choice(
                    direction_names,
                    size=int(np.random.choice([1, 2])),
                    replace=False,
                ),
            )
        else:
            chosen = sorted(scores, key=scores.get, reverse=True)[:2]
        add(profile, chosen)
        if progress_callback and i % 4000 == 0:
            progress_callback(6, len(data))

    # 5) балансировка: направление vs похожие — чёткий контраст
    dirs5 = direction_names
    for di, direction in enumerate(dirs5):
        others = [d for d in direction_names if d != direction]
        for _ in range(1000):
            profile = {f: 1.0 for f in feature_codes}
            for skill in skill_map.get(direction, []):
                profile[skill] = 5.0
            if others:
                rival = np.random.choice(others)
                for skill in skill_map.get(rival, []):
                    if skill not in skill_map.get(direction, []):
                        profile[skill] = 4.0
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(7, len(data))

    # 6) узкие профили — только 1-2 навыка направления
    dirs6 = direction_names
    for di, direction in enumerate(dirs6):
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {f: 1.0 for f in feature_codes}
            num_skills = min(int(np.random.choice([1, 2, 3])), len(key_skills))
            selected_skills = list(np.random.choice(key_skills, size=num_skills, replace=False))
            for skill in selected_skills:
                profile[skill] = 5.0
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(8, len(data))

    # 7) профили с высоким зарплатным ожиданием
    dirs7 = direction_names
    for di, direction in enumerate(dirs7):
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {
                f: 5.0 if f in key_skills else 1.0
                for f in feature_codes
            }
            profile['desired_salary'] = float(np.random.choice([150000, 200000, 300000]))
            add(profile, [direction])
        if progress_callback and di % 5 == 0:
            progress_callback(9, len(data))

    # 8) профили с низким зарплатным ожиданием (гибкие) — сильный контраст
    dirs8 = direction_names
    for di, direction in enumerate(dirs8):
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {
                f: 5.0 if f in key_skills else 1.0
                for f in feature_codes
            }
            profile['desired_salary'] = float(np.random.choice([60000, 80000]))
            add(profile, [direction])

    # 9) профили с ЕГЭ баллами — сильный контраст
    dirs9 = direction_names
    for di, direction in enumerate(dirs9):
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {
                f: 5.0 if f in key_skills else 1.0
                for f in feature_codes
            }
            for ege_col in EGE_SUBJECTS:
                if ege_col in feature_codes:
                    if any(s in EGE_BOOSTS.get(ege_col, []) for s in key_skills):
                        profile[ege_col] = int(np.random.uniform(75, 98))
                    else:
                        profile[ege_col] = int(np.random.uniform(40, 70))
            add(profile, [direction])

    # 10) смешанные профили с преобладанием 2-3 направлений — сильный контраст
    for i in range(15000):
        profile = {f: 1.0 for f in feature_codes}
        num_dirs = int(np.random.choice([2, 3]))
        selected = list(
            np.random.choice(direction_names, size=num_dirs, replace=False),
        )
        for idx, direction in enumerate(selected):
            weight = 5.0 - idx * 1.0  # первое: 5.0, второе: 4.0, третье: 3.0
            for skill in skill_map.get(direction, []):
                profile[skill] = min(5.0, weight)
        add(profile, selected)
    if progress_callback: progress_callback(10, len(data))

    return pd.DataFrame(data), multi_labels


def write_dataset_csv(df: 'object', output_path: Path) -> int:
    """Сохраняет обучающую выборку в CSV (utf-8-sig для Excel)."""
    import pandas as pd

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    return int(len(df))


def generate_dataset_csv(db: Session, output_path: Path) -> dict:
    """Синтетическая обучающая выборка по текущему каталогу → CSV."""
    feature_codes, direction_names, skill_map = load_config(db)
    if not feature_codes or not direction_names:
        raise RuntimeError('Нет активных признаков или направлений')
    df, multi_labels = generate_training_data(
        feature_codes, direction_names, skill_map,
    )
    rows = write_dataset_csv(df, output_path)
    return {
        'path': str(output_path),
        'rows': len(df),
        'features': feature_codes,
        'directions': direction_names,
    }


def generate_dataset_csv_progressive(
    db: Session, output_path: Path, progress_file: Path,
) -> dict:
    """Генерация с прогрессом в файл для polling."""
    import json as _json

    # Инициализируем файл прогресса сразу
    _json.dump({'step': 0, 'total': 10, 'rows': 0, 'progress': 0}, open(progress_file, 'w'))

    feature_codes, direction_names, skill_map = load_config(db)
    if not feature_codes or not direction_names:
        raise RuntimeError('Нет активных признаков или направлений')

    data = []
    multi_labels = []

    def _save_progress(step, rows):
        # step: 0-10, progress: 0-100 (cumulative)
        progress = min(100, round((step / 10) * 100))
        with open(progress_file, 'w') as f:
            _json.dump({'step': step, 'total': 10, 'rows': rows, 'progress': progress}, f)

    df, multi_labels = generate_training_data(
        feature_codes, direction_names, skill_map,
        progress_callback=lambda step, rows: _save_progress(step, rows),
    )
    
    # После завершения — записываем финальный прогресс как 100%
    _save_progress(10, len(df))
    
    # Записываем CSV на диск
    write_dataset_csv(df, output_path)
    
    # Сохраняем meta.json с количеством строк для админки
    meta_path = output_path.with_suffix('.meta.json')
    import json as _json
    meta_path.write_text(_json.dumps({
        'synthetic_rows': len(df),
        'features': feature_codes,
        'directions': direction_names,
        'updated_at': datetime.now().isoformat(),
    }, ensure_ascii=False))
    
    return {
        'path': str(output_path),
        'rows': len(df),
        'features': feature_codes,
        'directions': direction_names,
    }


def load_real_responses(
    csv_path: Path,
    feature_codes: list[str],
    direction_names: list[str],
) -> tuple['object', list[list[str]]]:
    """Реальные ответы из экспортированного responses.csv.

    Используются только строки с непустым chosen_fields (метки самооценки
    «какие направления вам подходят») — это дообучающие примеры.
    """
    import pandas as pd

    if not csv_path.exists():
        return pd.DataFrame(), []
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except Exception:  # noqa: BLE001
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f'Не удалось прочитать {csv_path}: {exc}') from exc

    known = set(direction_names)

    # Явный маппинг коротких названий → полные названия направлений
    SHORT_NAME_MAP: dict[str, str] = {
        'Химия': 'Физическая химия',
        'Химия и химическое производство': 'Физическая химия',
        'Инженерия': 'Инженерия систем искусственного интеллекта',
        'Программная инженерия': 'Технологии разработки программного обеспечения',
        'Программная инженерия и ИТ': 'Технологии разработки программного обеспечения',
        'ИТ': 'Инженерия систем искусственного интеллекта',
        'Информатика': 'Инженерия систем искусственного интеллекта',
        'Информатика и вычислительная техника': 'Инженерия систем искусственного интеллекта',
        'ИИ': 'Инженерия систем искусственного интеллекта',
        'Искусственный интеллект': 'Инженерия систем искусственного интеллекта',
        'Машинное обучение': 'Системы обработки данных и машинное обучение',
        'ML': 'Системы обработки данных и машинное обучение',
        'Автоматика': 'Электроника и автоматика физических установок',
        'Электроника': 'Электроника и автоматика физических установок',
        'Физика': 'Теоретическая и экспериментальная физика микромира',
        'Ядерная физика': 'Физика атомного ядра и частиц',
        'Ядерная энергетика': 'Интеллектуальная и возобновляемая энергетика',
        'Энергетика': 'Интеллектуальная и возобновляемая энергетика',
        'Биология': 'Ядерно-физические технологии в биологии и медицине',
        'Биотехнологии': 'Ядерно-физические технологии в биологии и медицине',
        'Био': 'Ядерно-физические технологии в биологии и медицине',
        'Психология': 'Психологическое консультирование и психодиагностика',
        'Психотерапия': 'Патопсихологическая диагностика и психотерапия',
        'Перевод': 'Перевод и межкультурная коммуникация',
        'Лингвистика': 'Перевод и межкультурная коммуникация',
        'Экология': 'Управление экологической безопасностью на производстве',
        'География': 'Геофизические методы поиска и разведки месторождений полезных ископаемых',
        'Геофизика': 'Геофизические методы поиска и разведки месторождений полезных ископаемых',
        'Авиация': 'Проектирование беспилотных летательных аппаратов',
        'БПЛА': 'Проектирование беспилотных летательных аппаратов',
        'Дизайн': 'Прикладная информатика в компьютерном дизайне',
        'Бизнес': 'Цифровые технологии в бизнесе',
        '1С': '1С технологии для бизнеса',
        '1с': '1С технологии для бизнеса',
        'Право': 'Гражданско-правовой',
        'Юриспруденция': 'Гражданско-правовой',
        'Уголовное право': 'Уголовно-правовой',
        'Маркетинг': 'Социологические и маркетинговые исследования',
        'Социология': 'Социологические и маркетинговые исследования',
        'Управление': 'Прикладная информатика в управлении корпоративными системами',
        'Разработка ПО': 'Технологии разработки программного обеспечения',
        'Разработка программ': 'Технологии разработки программного обеспечения',
        'Разработка систем': 'Разработка программно-информационных систем',
        'Системы': 'Разработка программно-информационных систем',
        'Данные': 'Системы обработки данных и машинное обучение',
        'Анализ данных': 'Системы обработки данных и машинное обучение',
        'Безопасность': 'Безопасность информационных систем',
        'Кибербезопасность': 'Безопасность информационных систем',
        'Информационная безопасность': 'Безопасность информационных систем',
        'Радиоэлектроника': 'Проектирование и технология интеллектуальных радиоэлектронных устройств',
        'РЭУ': 'Проектирование и технология интеллектуальных радиоэлектронных устройств',
        'Автономные': 'Автономные источники энергии',
        'Возобновляемая энергетика': 'Интеллектуальная и возобновляемая энергетика',
        'Робототехника': 'Интеллектуальные системы управления роботизированными технологическими процессами',
        'Роботы': 'Интеллектуальные системы управления роботизированными технологическими процессами',
        'Нанотехнологии': 'Инновационные материалы и нанотехнологии',
        'Материалы': 'Инновационные материалы и нанотехнологии',
        'Разведка': 'Геофизические методы поиска и разведки месторождений полезных ископаемых',
        'Месторождения': 'Геофизические методы поиска и разведки месторождений полезных ископаемых',
        'Конструирование': 'Конструирование и технология летательных аппаратов',
        'Летательные аппараты': 'Конструирование и технология летательных аппаратов',
        'Полёты': 'Конструирование и технология летательных аппаратов',
        'Ядерные': 'Физика ядерных реакций низких энергий',
        'Реакции': 'Физика ядерных реакций низких энергий',
        'Ядро': 'Физика ядерных реакций низких энергий',
    }

    def resolve_label(raw: str) -> list[str]:
        """Сопоставляет короткое название с полными названиями направлений."""
        raw = raw.strip()
        if raw in known:
            return [raw]

        # 1) Точный маппинг
        mapped = SHORT_NAME_MAP.get(raw)
        if mapped and mapped in known:
            return [mapped]

        # 2) Частичное совпадение: короткое название содержится в названии направления
        candidates = []
        raw_lower = raw.lower()
        for name in direction_names:
            name_lower = name.lower()
            # Короткое название содержится в полном
            if raw_lower in name_lower:
                candidates.append(name)
            # Полное название содержит ключевое слово
            elif len(raw_lower) > 2:
                # Разобьём короткое на слова и проверим, сколько содержится
                words = raw_lower.split()
                matches = sum(1 for w in words if w in name_lower)
                if matches >= max(1, len(words) // 2):
                    candidates.append(name)

        return candidates

    rows: list[dict] = []
    labels: list[list[str]] = []
    skipped_no_fields = 0
    skipped_no_match = 0
    for _, row in df.iterrows():
        raw_labels = str(row.get('chosen_fields', '') or '').strip()
        if not raw_labels:
            skipped_no_fields += 1
            continue
        parts = [name.strip() for name in raw_labels.split('|')]
        chosen: list[str] = []
        for part in parts:
            resolved = resolve_label(part)
            chosen.extend(resolved)
        if not chosen:
            skipped_no_match += 1
            continue
        profile: dict[str, float] = {}
        for code in feature_codes:
            raw = row.get(code)
            try:
                profile[code] = float(raw)
            except (TypeError, ValueError):
                # старые CSV без новых признаков (например, ege_*) — 0
                profile[code] = 0.0
        rows.append(profile)
        labels.append(chosen)
    
    total = len(df)
    kept = len(rows)
    if total > 0:
        print(f'  [real] Всего строк: {total}, сохранено: {kept}, пропущено (нет chosen_fields): {skipped_no_fields}, пропущено (направления не распознаны): {skipped_no_match}')
    return pd.DataFrame(rows), labels


def build_model(input_dim: int, num_classes: int) -> 'object':
    """Keras-модель (импортируется лениво)."""
    from tensorflow import keras
    from tensorflow.keras import layers

    inputs = keras.Input(shape=(input_dim,))
    x = layers.Dense(128, activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(64, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.5)(x)
    x = layers.Dense(32, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='sigmoid')(x)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(0.001),
        loss='binary_crossentropy',
        metrics=[keras.metrics.AUC(name='auc')],
    )
    return model


def compute_metrics(
    y_true: 'object',
    y_pred_proba: 'object',
    class_names: list[str],
) -> dict:
    import numpy as np
    from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

    y_pred_binary = (y_pred_proba >= 0.5).astype(int)
    n = len(y_true)

    top1 = top3 = top5 = 0
    for i in range(n):
        true = set(np.where(y_true[i] == 1)[0])
        if not true:
            continue
        order = np.argsort(y_pred_proba[i])[::-1]
        if order[0] in true:
            top1 += 1
        if any(idx in true for idx in order[:3]):
            top3 += 1
        if any(idx in true for idx in order[:5]):
            top5 += 1

    metrics = {
        'top1_accuracy': round(top1 / n, 4) if n else 0,
        'top3_accuracy': round(top3 / n, 4) if n else 0,
        'top5_accuracy': round(top5 / n, 4) if n else 0,
        'macro_precision': round(
            float(precision_score(y_true, y_pred_binary, average='macro', zero_division=0)), 4,
        ),
        'macro_recall': round(
            float(recall_score(y_true, y_pred_binary, average='macro', zero_division=0)), 4,
        ),
        'macro_f1': round(
            float(f1_score(y_true, y_pred_binary, average='macro', zero_division=0)), 4,
        ),
    }
    try:
        metrics['macro_auc'] = round(
            float(roc_auc_score(y_true, y_pred_proba, average='macro')), 4,
        )
    except ValueError:
        metrics['macro_auc'] = None

    per_class = f1_score(y_true, y_pred_binary, average=None, zero_division=0)
    metrics['per_class_f1'] = {
        name: round(float(score), 4)
        for name, score in zip(class_names, per_class)
    }
    
    # Метрики по каждому направлению
    from sklearn.metrics import precision_recall_fscore_support
    prec, rec, f1, sup = precision_recall_fscore_support(
        y_true, y_pred_binary, labels=list(range(len(class_names))), zero_division=0
    )
    metrics['per_direction'] = [
        {
            'label': name,
            'precision': round(float(p), 4),
            'recall': round(float(r), 4),
            'f1': round(float(f), 4),
            'support': int(s),
        }
        for name, p, r, f, s in zip(class_names, prec, rec, f1, sup)
    ]
    return metrics


def _previous_run_path(db: Session) -> Optional[Path]:
    """Путь к артефактам последнего успешного запуска (для дообучения)."""
    prev = db.scalar(
        select(ModelRun)
        .where(
            ModelRun.status == ModelRunStatus.completed,
            ModelRun.artifact_dir != '',
        )
        .order_by(ModelRun.id.desc())
        .limit(1),
    )
    return Path(prev.artifact_dir) if prev and prev.artifact_dir else None


def run_training(
    run_id: int,
    triggered_by: Optional[int] = None,
    dataset: str = 'all',
    real_data_path: Optional[str] = None,
    model_id: Optional[int] = None,
) -> None:
    """Фоновая задача: обучает модель и обновляет model_runs.

    dataset:
      - 'synthetic' — только синтетические данные;
      - 'all'       — синтетика + реальные ответы из CSV (responses.csv),
                      если файл существует. Реальные примеры повторяются ×4
                      (вес дообучения) и, при совпадении размерности,
                      модель дообучается от весов предыдущего запуска.

    Использует собственную сессию БД (не зависит от запросной).
    """
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
    from tensorflow import keras

    class _EpochSaverCallback(keras.callbacks.Callback):
        """Сохраняет текущую эпоху в ModelRun во время обучения."""

        def __init__(self, run_id, total_epochs):
            super().__init__()
            self.run_id = run_id
            self.total_epochs = total_epochs

        def on_epoch_end(self, epoch, logs=None):
            import os
            print(f'[trainer] Epoch {epoch+1}/{self.total_epochs} saved, PID={os.getpid()}', flush=True)
            db = SessionLocal()
            try:
                run = db.get(ModelRun, self.run_id)
                if run:
                    run.current_epoch = epoch + 1
                    run.total_epochs = self.total_epochs
                    db.commit()
                    print(f'[trainer] Epoch {epoch+1} COMMITTED to DB', flush=True)
            except Exception as exc:
                print(f'[trainer] Epoch save ERROR: {exc}', flush=True)
            finally:
                db.close()

    set_seed(42)
    settings = get_settings()
    import os
    print(f'[trainer] START run_id={run_id}, PID={os.getpid()}', flush=True)
    
    # Шаг 1: открываем сессию, ставим статус running, закрываем
    db_init = SessionLocal()
    try:
        run = db_init.get(ModelRun, run_id)
        if run is None:
            return
        run.status = ModelRunStatus.running
        db_init.commit()
        print(f'[trainer] Status set to running', flush=True)
    finally:
        db_init.close()

    try:
        print(f'[trainer] Loading config...', flush=True)
        feature_codes, direction_names, skill_map = load_config(None)
        print(f'[trainer] Config loaded: {len(feature_codes)} features, {len(direction_names)} directions', flush=True)
        if not feature_codes or not direction_names:
            raise RuntimeError('Нет активных признаков или направлений')

        print(f'[trainer] Generating training data...', flush=True)
        df, multi_labels = generate_training_data(
            feature_codes, direction_names, skill_map,
        )
        print(f'[trainer] Training data generated: {len(df)} rows', flush=True)
        dataset_info = {'synthetic': int(len(df))}

        # Fine-tuning: используем ТОЛЬКО реальные данные
        is_finetune = model_id is not None

        # Реальные ответы (дообучение на данных вуза из responses.csv)
        real_csv_path = Path(real_data_path) if real_data_path else (
            Path(settings.data_dir) / 'real' / 'responses.csv'
        )
        real_df, real_labels = load_real_responses(
            real_csv_path,
            feature_codes,
            direction_names,
        )
        print(f'[trainer] Real responses loaded: {len(real_df)} rows', flush=True)
        use_real = (
            dataset == 'all'
            and len(real_df) > 0
            and len(real_labels) > 0
        )
        use_real_only = (
            dataset == 'real_only'
            and len(real_df) > 0
            and len(real_labels) > 0
        )
        if is_finetune:
            # Fine-tuning: ТОЛЬКО реальные данные, без синтетики
            df = real_df.copy()
            multi_labels = real_labels.copy()
            dataset_info = {'real': int(len(real_labels)), 'synthetic': 0}
        elif use_real_only:
            # ТОЛЬКО реальные данные, без синтетики
            df = real_df.copy()
            multi_labels = real_labels.copy()
            dataset_info = {'real': int(len(real_labels)), 'synthetic': 0}
        elif use_real:
            # Заполняем NaN в реальных данных (синтетические все заполнены)
            for col in real_df.columns:
                if real_df[col].isna().any():
                    real_df[col] = real_df[col].fillna(0.0)
            # Просто объединяем синтетику и реальные данные
            synth_count = len(df)
            real_count = len(real_df)
            print(f'  [data] Синтетика: {synth_count}, реальные: {real_count}')
            df = pd.concat([df, real_df], ignore_index=True)
            multi_labels = multi_labels + real_labels
            dataset_info['real'] = real_count

        feature_cols = [c for c in df.columns if c != 'chosen_fields']
        X = df[feature_cols].values.astype('float32')

        mlb = MultiLabelBinarizer(classes=direction_names)
        y = mlb.fit_transform(multi_labels)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        total_samples = len(X_scaled)
        # Минимум 5 образцов для train_test_split с validation_split=0.2
        if total_samples < 5:
            raise RuntimeError(
                f'Выборка слишком мала: {total_samples} образцов. '
                f'Минимум 5 для обучения. Загрузите больше реальных ответов (responses.csv) '
                f'или сгенерируйте синтетическую выборку.'
            )

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42,
        )

        # Fine-tuning: стартуем от весов выбранной модели
        model = None
        fine_tuned_from = None
        if model_id is not None:
            prev_run_db = SessionLocal()
            try:
                prev_run = prev_run_db.get(ModelRun, model_id)
                if prev_run and prev_run.artifact_dir:
                    prev_path = Path(prev_run.artifact_dir)
                    if prev_path.exists() and (prev_path / 'model.keras').exists():
                        try:
                            candidate = keras.models.load_model(
                                prev_path / 'model.keras', compile=False,
                            )
                            out_dim = (
                                candidate.output_shape[-1]
                                if hasattr(candidate.output_shape, '__getitem__')
                                else None
                            )
                            if (
                                candidate.input_shape[-1] == X.shape[1]
                                and out_dim == len(direction_names)
                            ):
                                model = candidate
                                fine_tuned_from = str(prev_path)
                        except Exception:  # noqa: BLE001
                            model = None
            finally:
                prev_run_db.close()
        if model is None:
            model = build_model(X.shape[1], len(direction_names))

        lr = 0.0001 if fine_tuned_from else 0.001
        model.compile(
            optimizer=keras.optimizers.Adam(lr),
            loss='binary_crossentropy',
            metrics=[keras.metrics.AUC(name='auc')],
        )
        print(f'[trainer] Starting model.fit: {len(X_train)} train, {len(X_test)} test samples, 80 epochs', flush=True)
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_auc',
                patience=10,
                restore_best_weights=True,
            ),
            _EpochSaverCallback(run_id, 80),
        ]
        history = model.fit(
            X_train, y_train,
            validation_split=0.2,
            epochs=80,
            batch_size=32,
            callbacks=callbacks,
            verbose=0,
        )
        print(f'[trainer] model.fit completed', flush=True)

        # Сохраняем историю обучения по эпохам
        epochs_data = []
        val_auc_history = history.history.get('val_auc', [])
        val_loss_history = history.history.get('val_loss', [])
        for i in range(len(val_auc_history)):
            epochs_data.append({
                'epoch': i + 1,
                'val_auc': round(float(val_auc_history[i]), 4),
                'val_loss': round(float(val_loss_history[i]), 4),
            })

        y_pred_proba = model.predict(X_test, verbose=0)
        metrics = compute_metrics(y_test, y_pred_proba, direction_names)
        metrics['final_val_auc'] = round(
            float(np.max(history.history.get('val_auc', [0]))), 4,
        )
        metrics['epochs_history'] = epochs_data

        artifact_dir = Path(settings.models_dir) / f'run_{run_id}'
        artifact_dir.mkdir(parents=True, exist_ok=True)
        model.save(artifact_dir / 'model.keras')
        joblib.dump(scaler, artifact_dir / 'scaler.pkl')
        joblib.dump(mlb, artifact_dir / 'mlb.pkl')
        config = {
            'features': feature_codes,
            'directions': direction_names,
            'skills': skill_map,
            'dataset': dataset_info,
            'fine_tuned_from': fine_tuned_from,
            'trained_at': datetime.now().isoformat(timespec='seconds'),
            'metrics': metrics,
        }
        config = _clean_nan(config)
        (artifact_dir / 'config.json').write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        # Шаг 3: открываем новую сессию для финальной записи
        db_final = SessionLocal()
        try:
            run = db_final.get(ModelRun, run_id)
            if run:
                run.status = ModelRunStatus.completed
                run.artifact_dir = str(artifact_dir)
                run.metrics = _clean_nan(metrics)
                run.config_snapshot = {
                    'features': feature_codes,
                    'directions': direction_names,
                    'skills': skill_map,
                    'dataset_type': run.config_snapshot.get('dataset_type', run.config_snapshot.get('dataset', dataset)),
                    'dataset_info': dataset_info,
                    'fine_tuned_from': fine_tuned_from,
                }
                run.error_message = ''
                run.finished_at = datetime.now()
                db_final.commit()
        finally:
            db_final.close()

    except Exception as exc:  # noqa: BLE001
        # При ошибке тоже обновляем статус
        db_err = SessionLocal()
        try:
            run = db_err.get(ModelRun, run_id)
            if run:
                run.status = ModelRunStatus.failed
                run.error_message = str(exc)
                run.finished_at = datetime.now()
                db_err.commit()
        finally:
            db_err.close()