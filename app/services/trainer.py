"""Сервис обучения: динамический тренировщик на конфигурации из БД.

Признаки, направления и ключевые навыки читаются из PostgreSQL.
Артефакты сохраняются в {models_dir}/run_{id}/ (модель, scaler, mlb,
config.json). Каждый запуск — отдельная строка model_runs, что позволяет
хранить несколько версий модели и не ломать работающую.

Тяжёлые ML-зависимости (numpy, pandas, tensorflow, sklearn) импортируются
лениво — внутри функций, поэтому модуль можно импортировать без них.
"""
from __future__ import annotations

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
from app.services.feature_normalization import normalize_dataframe_ege


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
        'economic_analysis', 'ai_ml', 'cybersecurity', 'geology',
    ],
    'ege_russian': [
        'communication_skill', 'legal_knowledge', 'social_research',
        'psychological_counseling', 'linguistics_skill', 'management',
        'public_administration', 'design',
    ],
    'ege_informatics': [
        'computer_systems', 'software_development', 'it_infrastructure',
        'algorithms_theory', 'automation_tech', 'business_analytics',
        'ai_ml', 'cybersecurity', 'geology',
    ],
    'ege_physics': [
        'experimental_physics', 'nuclear_physics', 'power_engineering',
        'electronics', 'aerospace_design', 'automation_tech',
        'chemical_analysis', 'geology', 'ai_ml',
    ],
    'ege_chemistry': ['chemical_analysis', 'biotech'],
    'ege_biology': ['ecology', 'psychological_counseling', 'biotech'],
    'ege_social': [
        'management', 'public_administration', 'economic_analysis',
        'legal_knowledge', 'social_research', 'psychological_counseling',
        'business_analytics',
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
    """3-4 сданных ЕГЭ (релевантные + обязательные), остальные = 0 баллов.

    Каноническая шкала ЕГЭ — баллы 0-100 (как в реальном опросе).
    Несданные предметы = 0 баллов, сданные профильные = 55-95,
    обязательные = 50-90, у отличников все сданные = 80-100.
    Приведение к шкале 1-5 выполняется единообразно перед обучением
    (см. app.services.feature_normalization.normalize_dataframe_ege).
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

    # Реалистичная вариативность ЕГЭ — иначе ЕГЭ-паттерн становится
    # «фингерпринтом» направления: модель учится определять направление
    # по набору сданных предметов и игнорирует навыки (наблюдаемый баг:
    # отклонение реального профиля от идеального паттерна обнуляло
    # вероятность родственного направления).
    # Сданные = профильные (с небольшим шансом пропуска) + обязательные
    # + 0-2 случайных предмета.
    droppable = [s for s in relevant if np.random.random() < 0.15]
    extra = [
        s for s in EGE_SUBJECTS
        if s not in relevant and s not in mandatory
        and s in profile and np.random.random() < 0.25
    ]
    taken = list(set(relevant + mandatory + extra) - set(droppable))

    # ВСЕ несданные = 0 баллов (не сдавал)
    for subject in EGE_SUBJECTS:
        if subject in profile and subject not in taken:
            profile[subject] = 0

    # Сданные = баллы 0-100
    for subject in taken:
        if subject not in profile:
            continue
        if all_high:
            score = float(np.random.uniform(70.0, 100.0))
        elif subject in relevant:
            score = float(np.random.uniform(55.0, 95.0))
        elif subject in mandatory:
            score = float(np.random.uniform(50.0, 90.0))
        else:
            score = float(np.random.uniform(45.0, 85.0))
        profile[subject] = int(round(max(0.0, min(100.0, score))))


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
    
    Реалистичные профили: ключевые навыки = 3.5-5.0, неключевые = 2.0-4.0.
    Модель учится на данных, похожих на реальные ответы в опросе.
    """
    import numpy as np
    import pandas as pd

    data = []
    multi_labels = []

    n_dirs = len(direction_names) or 1
    # Ожидаемый объём выборки — для расчёта процента прогресса
    target_rows = n_dirs * (3000 + 1000 + 1000 + 1000 + 300) + 5000

    def report_progress():
        if progress_callback:
            pct = min(95, round(len(data) / target_rows * 100))
            progress_callback(pct, len(data))

    def add(profile: dict, labels: list[str], all_high: bool = False):
        profile['desired_salary'] = float(np.random.choice(SALARY_CHOICES))
        _fill_ege(profile, labels, skill_map, all_high=all_high)
        profile['chosen_fields'] = labels
        data.append(profile)
        multi_labels.append(labels)

    # 1) РЕАЛИСТИЧНЫЕ (3000/направление) — ВСЕ key-навыки высокие (3.5-5.0).
    # Принципиально: направления с одинаковым набором key-навыков («двойники»,
    # напр. «Технологии разработки ПО» и «Разработка ПИС») получают
    # ИДЕНТИЧНЫЕ кластеры — модель честно выдаёт им близкие проценты.
    # Прежние произвольные per-направленческие «профили-ловушки» приводили
    # к абсурду: программист с sd=5 получал 6% у родственного направления.
    for direction in direction_names:
        key_skills = skill_map.get(direction, [])
        for _ in range(3000):
            profile = {}
            for f in feature_codes:
                if f in key_skills:
                    profile[f] = float(np.random.normal(4.3, 0.35))
                    profile[f] = max(3.5, min(5.0, profile[f]))
                else:
                    profile[f] = float(np.random.normal(3.0, 0.4))
                    profile[f] = max(2.0, min(4.0, profile[f]))
            add(profile, [direction])
        report_progress()

    # 1b) СРЕДНИЕ ПРОФИЛИ (1000/направление) — key-навыки 3.3-4.6:
    # профиль с умеренным интересом к области тоже узнаваем.
    for direction in direction_names:
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {}
            for f in feature_codes:
                if f in key_skills:
                    profile[f] = float(np.random.normal(3.9, 0.3))
                    profile[f] = max(3.3, min(4.6, profile[f]))
                else:
                    profile[f] = float(np.random.normal(3.0, 0.4))
                    profile[f] = max(2.0, min(4.0, profile[f]))
            add(profile, [direction])
        report_progress()

    # 2) ОТЛИЧНИКИ — все навыки 4.0-5.0
    for di, direction in enumerate(direction_names):
        for _ in range(1000):
            profile = {f: float(np.random.uniform(4.0, 5.0)) for f in feature_codes}
            add(profile, [direction], all_high=True)
        report_progress()

    # 3) МУЛЬТИ-НАПРАВЛЕНИЯ — 2-3 направления с разными баллами
    for i in range(5000):
        profile = {f: float(np.random.normal(3.0, 0.4)) for f in feature_codes}
        profile = {f: max(2.0, min(4.0, v)) for f, v in profile.items()}
        
        max_dirs = min(3, len(direction_names))
        if max_dirs >= 2:
            num_dirs = int(np.random.choice(range(2, max_dirs + 1)))
        else:
            num_dirs = 1
        selected = list(np.random.choice(direction_names, size=num_dirs, replace=False))
        
        for direction in selected:
            for skill in skill_map.get(direction, []):
                profile[skill] = float(np.random.normal(4.2, 0.3))
                profile[skill] = max(3.0, min(5.0, profile[skill]))
        
        for trait in ('logical_thinking', 'memory_ability', 'problem_solving'):
            if trait in profile:
                profile[trait] = float(np.random.uniform(3.5, 4.5))
        add(profile, selected)
        if i % 500 == 0:
            report_progress()

    # 4) СЛАБЫЕ ПРОФИЛИ — ключевые ~3.3, остальные ~2.5.
    # Важно: key-навыки не ровно 3.0 — иначе слабый интерес к области
    # (например, legal=3 у гос-профиля) буквально совпадает со слабым
    # кластером узкого направления и «крадёт» рекомендацию.
    for direction in direction_names:
        key_skills = skill_map.get(direction, [])
        for _ in range(1000):
            profile = {}
            for f in feature_codes:
                if f in key_skills:
                    profile[f] = float(np.random.normal(3.3, 0.3))
                    profile[f] = max(2.8, min(3.9, profile[f]))
                else:
                    profile[f] = float(np.random.normal(2.5, 0.3))
                    profile[f] = max(2.0, min(3.0, profile[f]))
            add(profile, [direction])
        report_progress()

    # 5) БЕЗ ЕГЭ — пользователь не сдавал ни одного предмета (все ege_* = 0).
    # Без этого блока профили «все ЕГЭ = 0» вне обучающего распределения:
    # модель экстраполирует и выдаёт бессмысленный топ (наблюдаемый баг).
    has_ege = any(c.startswith('ege_') for c in feature_codes)
    if has_ege:
        for direction in direction_names:
            key_skills = skill_map.get(direction, [])
            for _ in range(300):
                profile = {}
                for f in feature_codes:
                    if f.startswith('ege_'):
                        profile[f] = 0
                    elif f in key_skills:
                        base = 2.6 + 2.3 * float(np.random.uniform(0.7, 1.0))
                        profile[f] = float(np.random.normal(base, 0.35))
                        profile[f] = max(3.2, min(5.0, profile[f]))
                    elif f == 'desired_salary':
                        continue
                    else:
                        profile[f] = float(np.random.normal(3.0, 0.4))
                        profile[f] = max(2.0, min(4.0, profile[f]))
                add(profile, [direction])
            report_progress()

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

    def _save_progress(progress_pct, rows):
        # progress_pct: 0-100 (плавный, считается по объёму сгенерированных строк)
        progress = min(100, max(0, int(progress_pct)))
        with open(progress_file, 'w') as f:
            _json.dump({
                'step': progress, 'total': 100,
                'rows': rows, 'progress': progress,
                'done': progress >= 100,
            }, f)

    df, multi_labels = generate_training_data(
        feature_codes, direction_names, skill_map,
        progress_callback=lambda pct, rows: _save_progress(pct, rows),
    )

    # После завершения — записываем финальный прогресс как 100%
    _save_progress(100, len(df))
    
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

    import numpy as _np

    # Accuracy:
    #  - accuracy — средняя доля верных решений по всем меткам (Hamming accuracy)
    #  - subset_accuracy — все метки примера угаданы точно (strict match)
    correct = (_np.asarray(y_pred_binary) == _np.asarray(y_true))
    hamming_acc = float(correct.mean()) if n else 0.0
    subset_acc = float(correct.all(axis=1).mean()) if n else 0.0

    metrics = {
        'top1_accuracy': round(top1 / n, 4) if n else 0,
        'top3_accuracy': round(top3 / n, 4) if n else 0,
        'top5_accuracy': round(top5 / n, 4) if n else 0,
        'accuracy': round(hamming_acc, 4),
        'subset_accuracy': round(subset_acc, 4),
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
        if run.status == ModelRunStatus.failed:
            # Отменён ещё до старта
            print('[trainer] Run отменён до старта — не запускаю', flush=True)
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

        # Единая нормализация ЕГЭ (0-100 → 1-5) для синтетики и реальных данных
        df = normalize_dataframe_ege(df, feature_codes)

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
        early_stopping_kwargs = {
            'monitor': 'val_auc',
            'patience': 10,
            'restore_best_weights': True,
            # Ранняя остановка до 30 эпох оставляла «мёртвые» классы
            'start_from_epoch': 30,
        }
        try:
            early_stop = keras.callbacks.EarlyStopping(**early_stopping_kwargs)
        except TypeError:  # старые версии TF без start_from_epoch
            early_stopping_kwargs.pop('start_from_epoch')
            early_stop = keras.callbacks.EarlyStopping(**early_stopping_kwargs)
        callbacks = [early_stop, _EpochSaverCallback(run_id, 80)]
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

        # Temperature scaling: калибровка вероятностей на тестовой выборке
        # Подбираем T, который максимизирует top-1 accuracy
        best_temp, best_acc = 1.0, metrics.get('top1_accuracy', 0)
        for t in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0]:
            scaled = np.power(y_pred_proba, 1.0 / t)
            scaled = scaled / scaled.sum(axis=1, keepdims=True)
            preds = np.argmax(scaled, axis=1)
            true_labels = np.argmax(y_test, axis=1)
            acc = np.mean(preds == true_labels)
            if acc > best_acc:
                best_acc = acc
                best_temp = t
        metrics['calibration_temperature'] = round(best_temp, 2)
        metrics['calibration_accuracy'] = round(best_acc, 4)
        print(f'[trainer] Temperature scaling: T={best_temp}, acc={best_acc:.4f}', flush=True)

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
            'temperature': best_temp,
        }
        config = _clean_nan(config)
        (artifact_dir / 'config.json').write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

        # Шаг 3: открываем новую сессию для финальной записи.
        # Если обучение было отменено (админ выставил failed) — не трогаем
        # статус: ран остаётся отменённым.
        db_final = SessionLocal()
        try:
            run = db_final.get(ModelRun, run_id)
            if run and run.status == ModelRunStatus.failed:
                print('[trainer] Обучение было отменено — артефакты не сохраняются', flush=True)
                return
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
                    # Не теряем базовую модель — админка показывает «Fine-tuning от модели #N»
                    'fine_tuned_from_run': run.config_snapshot.get('fine_tuned_from_run'),
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