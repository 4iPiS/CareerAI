#!/usr/bin/env python3
"""CLI: рекомендации направлений по CSV-профилю студента."""

import argparse
import os
import sys
import warnings
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
warnings.filterwarnings('ignore')

import logging
import pandas as pd
import tensorflow as tf

logging.getLogger('absl').setLevel(logging.ERROR)
tf.get_logger().setLevel('ERROR')
tf.autograph.set_verbosity(0)

from career_core import CareerAdvisor
from config.model_config import UNIVERSITY_NAME


def print_recommendations(recommendations):
    print('\n' + '=' * 70)
    print('ВАШИ РЕКОМЕНДАЦИИ')
    print('=' * 70)

    indicators = {
        'IDEAL': '🟢',
        'EXCELLENT': '🔵',
        'GOOD': '🟡',
        'AVERAGE': '⚪',
        'LOW': '⚪',
    }

    for rec in recommendations:
        indicator = indicators.get(rec['match_level'], '⚪')
        print(f"\n{indicator} {rec['rank']}. {rec['field']}")
        if rec.get('code'):
            print(f"   Код ФГОС: {rec['code']}")
        print(f"   Вероятность: {rec['probability']}% ({rec['match_level']})")
        print(f"   {rec['description']}")
        if rec.get('explanation'):
            print(f"   {rec['explanation']}")
        if rec.get('key_skills'):
            print(f"   Ключевые навыки: {rec['key_skills']}")
        print('-' * 50)

    print('=' * 70)


def main():
    parser = argparse.ArgumentParser(
        description='CareerAI — рекомендации направлений Университета «Дубна»',
    )
    parser.add_argument('csv_file', help='CSV с одной строкой профиля (27 признаков)')
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Папка для CSV/JSON (по умолчанию: output)',
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Сохранить полный отчёт в JSON',
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_file)
    if not csv_path.exists():
        print(f'ERROR: файл не найден: {csv_path}')
        sys.exit(1)

    print('\n' + '=' * 70)
    print('CareerAI — профориентационный помощник')
    print(UNIVERSITY_NAME)
    print('=' * 70)

    print('\nЗагрузка модели...')
    advisor = CareerAdvisor()
    try:
        advisor.load_model()
    except FileNotFoundError as exc:
        print(f'ERROR: {exc}')
        sys.exit(1)

    print(f'Модель загружена: {len(advisor.mlb.classes_)} направлений')
    print(f'Анализ профиля: {csv_path}')

    student_data = pd.read_csv(csv_path)
    recommendations, _, profile = advisor.get_recommendations(student_data)
    print_recommendations(recommendations)

    paths = advisor.save_results(
        recommendations,
        profile,
        output_dir=args.output_dir,
        detailed=args.detailed,
        source_csv=str(csv_path),
    )
    print(f"\nРезультаты сохранены: {paths['csv']}")
    if 'json' in paths:
        print(f"Подробный отчёт: {paths['json']}")


if __name__ == '__main__':
    main()
