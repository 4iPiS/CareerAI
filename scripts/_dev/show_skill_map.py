"""Карта навыков направлений + уровни emphasis для спорных областей."""
import sys

sys.path.insert(0, '/app')

from app.services.trainer import load_config

feature_codes, direction_names, skill_map = load_config(None)
for name in direction_names:
    print(f'{name}: {skill_map.get(name)}')
