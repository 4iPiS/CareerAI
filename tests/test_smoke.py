"""Базовые проверки конфигурации: направления и признаки.

Два слоя каталога:
- базовый (config/model_config.py) — 21 агрегированное направление, 32 признака;
- продакшен-слой (стартовые скрипты) — 31 активная программа (профили), 43 признака.
"""

from config.model_config import (
    DIRECTION_KEY_SKILLS,
    DUBNA_DIRECTION_KEYS,
    EXPANDED_FEATURES,
)


def test_base_catalog_consistency():
    """Базовый слой сида: 21 агрегированное направление + 32 признака."""
    assert len(DUBNA_DIRECTION_KEYS) == 21
    assert len(EXPANDED_FEATURES) == 32
    assert set(DIRECTION_KEY_SKILLS.keys()) == set(DUBNA_DIRECTION_KEYS)


def test_production_catalog_has_31_programs_and_43_features():
    """Продакшен-каталог после стартовых скриптов: 31 программа, 43 признака."""
    from scripts.add_ege import EGE_FEATURES
    from scripts.sync_directions import PROGRAMS

    assert len(PROGRAMS) == 31
    assert len(EGE_FEATURES) == 11
    # 32 базовых признака + 11 признаков ЕГЭ
    assert len(EXPANDED_FEATURES) + len(EGE_FEATURES) == 43

    names = {p[0] for p in PROGRAMS}
    assert len(names) == len(PROGRAMS)  # без дубликатов имён
    for _name, code, years, _ege, skills in PROGRAMS:
        assert len(code.replace('.', '')) == 6  # код ФГОС вида 00.00.00
        assert years in (4, 5)  # срок обучения
        assert skills  # у каждой программы есть ключевые навыки
        assert all(s in EXPANDED_FEATURES for s in skills)
