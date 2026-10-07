"""Тест миграции старых CSV-ответов в PostgreSQL-схему."""

from sqlalchemy import select

from app.models import Feedback, SurveySession


def test_migrate_responses_csv(db_session, tmp_path, monkeypatch):
    import scripts.migrate_responses as migrate_mod

    csv_path = tmp_path / 'responses.csv'
    csv_path.write_text(
        'session_id,created_at,source,questions_asked,software_development,desired_salary,'
        'rec1_field,rec1_probability,chosen_fields,feedback_score,label_source\n'
        'sess1,2026-01-01T10:00:00,web,30,5,120000,Программная инженерия,90,'
        'Программная инженерия|Информатика и вычислительная техника,4,self_report\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(migrate_mod, 'SessionLocal', lambda: db_session)
    count = migrate_mod.migrate(csv_path)
    assert count == 1

    session = db_session.scalar(select(SurveySession))
    assert session.session_uuid == 'sess1'
    assert session.status == 'completed'
    assert session.profile['software_development'] == 5.0
    assert session.profile['desired_salary'] == 120000
    assert session.recommendations[0]['field'] == 'Программная инженерия'

    feedback = db_session.scalar(select(Feedback))
    assert feedback.chosen_fields == [
        'Программная инженерия',
        'Информатика и вычислительная техника',
    ]
    assert feedback.feedback_score == 4


def test_migrate_skips_existing(db_session, tmp_path, monkeypatch):
    import scripts.migrate_responses as migrate_mod

    csv_path = tmp_path / 'responses.csv'
    csv_path.write_text(
        'session_id,software_development,desired_salary\nsess1,5,120000\nsess2,4,80000\n',
        encoding='utf-8',
    )
    db_session.add(SurveySession(
        session_uuid='sess1', stage='done', status='completed',
        answers={}, profile={}, recommendations=[], custom_data={}, state={},
    ))
    db_session.commit()

    monkeypatch.setattr(migrate_mod, 'SessionLocal', lambda: db_session)
    count = migrate_mod.migrate(csv_path)
    assert count == 1  # импортирована только sess2