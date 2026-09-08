"""Базовые проверки конфигурации и (при наличии) обученной модели."""

from pathlib import Path

import pandas as pd
import pytest

from config.model_config import (
    DIRECTION_KEY_SKILLS,
    DUBNA_DIRECTION_KEYS,
    EXPANDED_FEATURES,
)
from career_core import CareerAdvisor, profile_from_dataframe
from train_model import generate_training_data


def test_directions_and_features_consistency():
    assert len(DUBNA_DIRECTION_KEYS) == 19
    assert len(EXPANDED_FEATURES) == 27
    assert set(DIRECTION_KEY_SKILLS.keys()) == set(DUBNA_DIRECTION_KEYS)


def test_training_data_generation():
    df, labels = generate_training_data()
    assert len(df) > 1000
    assert len(labels) == len(df)
    for col in EXPANDED_FEATURES:
        assert col in df.columns


def test_profile_defaults_from_partial_csv(tmp_path):
    partial = {EXPANDED_FEATURES[0]: 5.0, 'desired_salary': 120000}
    df = pd.DataFrame([partial])
    profile = profile_from_dataframe(df)
    assert profile[EXPANDED_FEATURES[0]] == 5.0
    assert profile['computer_systems'] == 3.0


def test_data_collector_writes_csv(tmp_path, monkeypatch):
    import data_collector as dc

    monkeypatch.setattr(dc, 'REAL_DATA_DIR', tmp_path)
    monkeypatch.setattr(dc, 'RESPONSES_CSV', tmp_path / 'responses.csv')

    profile = {f: 3.0 for f in EXPANDED_FEATURES}
    profile['software_development'] = 5.0
    recs = [{'field': 'Программная инженерия', 'probability': 90.0, 'rank': 1}]
    dc.save_response('test_sess', profile, recs)
    dc.update_labels('test_sess', ['Программная инженерия'], feedback_score=4)

    assert (tmp_path / 'responses.csv').exists()
    rows = dc._read_all_rows()
    assert len(rows) == 1
    assert rows[0]['chosen_fields'] == 'Программная инженерия'
    assert rows[0]['software_development'] == '5.0'


@pytest.mark.skipif(
    not Path('career_model/career_model.keras').exists(),
    reason='Модель не обучена — запустите python train_model.py',
)
def test_prediction_on_example_profile():
    advisor = CareerAdvisor()
    advisor.load_model()
    df = pd.read_csv('examples/student_it_profile.csv')
    recommendations, _, _ = advisor.get_recommendations(df)
    assert len(recommendations) == 5
    fields = {rec['field'] for rec in recommendations}
    it_related = {
        'Программная инженерия',
        'Информатика и вычислительная техника',
        'Прикладная информатика',
        'Информационные системы и технологии',
    }
    assert fields & it_related
