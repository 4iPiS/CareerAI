#!/usr/bin/env python3
"""Проверка: какие screening вопросы задаются и какие признаки заполняются."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Question, Feature, QuestionGroup, SurveySession


def main():
    print('=== Check screening questions ===')
    with SessionLocal() as db:
        # Все screening вопросы
        questions = db.scalars(
            select(Question)
            .join(QuestionGroup)
            .where(QuestionGroup.code == 'screening')
            .order_by(Question.sort_order)
        ).all()
        
        print(f'Total screening questions: {len(questions)}')
        for q in questions[:10]:
            feat = db.scalar(select(Feature).where(Feature.id == q.feature_id)) if q.feature_id else None
            print(f'  id={q.id} sort={q.sort_order} feature_id={q.feature_id} feature_code={feat.code if feat else "NONE"} text={q.text[:50]}')

        print()
        
        # Пример профиля сессии
        s = db.query(SurveySession).filter(SurveySession.status == 'completed').first()
        state = s.state or {}
        answers = state.get('answers', {})
        
        print('=== state[answers] (значения > 1) ===')
        for k, v in sorted(answers.items(), key=lambda x: -x[1] if isinstance(x[1], (int,float)) else 0):
            if isinstance(v, (int,float)) and v > 1:
                print(f'  {k}: {v}')
        
        print()
        print('=== profile (значения > 1) ===')
        profile = s.profile or {}
        for k, v in sorted(profile.items(), key=lambda x: -x[1] if isinstance(x[1], (int,float)) else 0):
            if isinstance(v, (int,float)) and v > 1:
                print(f'  {k}: {v}')
        
        print()
        print('=== Profile keys with value 1.0 (first 10) ===')
        count = 0
        for k, v in sorted(profile.items(), key=lambda x: x[0]):
            if isinstance(v, (int,float)) and v == 1.0:
                print(f'  {k}: {v}')
                count += 1
                if count >= 10:
                    break

    print('=== Done ===')


if __name__ == '__main__':
    main()
