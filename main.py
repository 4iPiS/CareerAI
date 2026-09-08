#!/usr/bin/env python3
"""FastAPI: веб-опросник и рекомендации CareerAI."""

import os
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import tensorflow as tf

from ask_questions import AdaptiveQuestionnaireV4
from career_core import CareerAdvisor, to_python
from config.model_config import DUBNA_DIRECTION_KEYS, EXPANDED_FEATURES
from data_collector import save_response, update_labels

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore')
tf.get_logger().setLevel('ERROR')

Path('static').mkdir(exist_ok=True)
Path('templates').mkdir(exist_ok=True)

app = FastAPI(title='CareerAI')
app.mount('/static', StaticFiles(directory='static'), name='static')

advisor = CareerAdvisor()
sessions: Dict[str, Any] = {}


@app.on_event('startup')
async def startup():
    try:
        advisor.load_model()
        print(f'[+] Модель загружена: {len(advisor.mlb.classes_)} направлений')
    except FileNotFoundError as exc:
        print(f'[!] {exc}')


@app.get('/', response_class=HTMLResponse)
async def index():
    html_path = Path('templates/index.html')
    return HTMLResponse(content=html_path.read_text(encoding='utf-8'))


@app.post('/api/start')
async def start_session():
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    questionnaire = AdaptiveQuestionnaireV4()
    sessions[session_id] = {
        'questionnaire': questionnaire,
        'stage': 'screening',
        'screening_idx': 0,
        'answers': {},
        'current_interest': None,
        'current_skill': None,
        'current_q_idx': 0,
        'pending_interests': [],
        'last_answer': None,
    }
    trait, name = questionnaire.SCREENING_QUESTIONS[0]
    return JSONResponse({
        'session_id': session_id,
        'question': {'id': trait, 'text': name},
        'progress': {
            'stage': 'screening',
            'current': 1,
            'total': len(questionnaire.SCREENING_QUESTIONS),
        },
    })


@app.post('/api/answer')
async def process_answer(request: Request):
    try:
        data = await request.json()
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        answer = data.get('answer')
        if session_id not in sessions:
            return JSONResponse({'error': 'Session not found'}, status_code=404)

        session = sessions[session_id]
        q = session['questionnaire']
        q.answers[question_id] = answer
        q.directly_asked_traits.add(question_id)
        q.questions_asked += 1

        stage = session['stage']
        if stage == 'screening':
            return await handle_screening(session_id, question_id, answer)
        if stage == 'detailed':
            return await handle_detailed(session_id, answer)
        if stage == 'personal':
            return await handle_personal(session_id, answer)
        if stage == 'salary':
            return await handle_salary(session_id, answer)
        return JSONResponse({'error': 'Unknown stage'}, status_code=400)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return JSONResponse({'error': str(exc)}, status_code=500)


async def handle_screening(session_id: str, question_id: str, answer: int):
    session = sessions[session_id]
    q = session['questionnaire']
    q.interests[question_id] = answer
    session['screening_idx'] += 1

    if session['screening_idx'] >= len(q.SCREENING_QUESTIONS):
        pending = []
        for trait, score in q.interests.items():
            if score >= 3 and trait in q.SKILL_QUESTIONS:
                pending.append(trait)
        if q.interests.get('computer_systems', 0) >= 3 and 'it_infrastructure' in q.SKILL_QUESTIONS:
            if 'it_infrastructure' not in pending:
                pending.append('it_infrastructure')
        if (
            q.interests.get('business_analytics', 0) >= 3
            or q.interests.get('management', 0) >= 3
        ) and 'economic_analysis' in q.SKILL_QUESTIONS:
            if 'economic_analysis' not in pending:
                pending.append('economic_analysis')

        session['pending_interests'] = pending
        session['stage'] = 'detailed'
        session['current_interest'] = None
        session['current_skill'] = None
        session['current_q_idx'] = 0
        session['last_answer'] = None
        return await get_next_question(session_id)

    trait, name = q.SCREENING_QUESTIONS[session['screening_idx']]
    return JSONResponse({
        'question': {'id': trait, 'text': name},
        'progress': {
            'stage': 'screening',
            'current': session['screening_idx'] + 1,
            'total': len(q.SCREENING_QUESTIONS),
        },
    })


async def handle_detailed(session_id: str, answer: int):
    session = sessions[session_id]
    if session.get('current_skill'):
        q = session['questionnaire']
        q.answers[session['current_skill']] = answer
        q.directly_asked_traits.add(session['current_skill'])
        q.questions_asked += 1
        session['last_answer'] = answer
    return await get_next_question(session_id)


async def handle_personal(session_id: str, answer: int):
    session = sessions[session_id]
    q = session['questionnaire']
    personal_traits = session.get('personal_traits', [])
    current_idx = session.get('personal_idx', 0)

    if current_idx < len(personal_traits):
        trait = personal_traits[current_idx]
        q.answers[trait] = answer
        q.directly_asked_traits.add(trait)
        q.questions_asked += 1
        session['personal_idx'] = current_idx + 1

    if session.get('personal_idx', 0) >= len(personal_traits):
        session['stage'] = 'salary'
        return JSONResponse({
            'question': {
                'id': 'salary',
                'text': 'Какую желаемую зарплату (в рублях) вы ожидаете?',
            },
            'is_salary': True,
        })

    trait = personal_traits[session['personal_idx']]
    text = q.COMMON_TRAITS.get(trait, f'Оцените {trait}?')
    return JSONResponse({
        'question': {'id': trait, 'text': text},
        'progress': {
            'stage': 'personal',
            'current': session['personal_idx'] + 1,
            'total': len(personal_traits),
        },
    })


async def handle_salary(session_id: str, answer: int):
    session = sessions[session_id]
    q = session['questionnaire']
    salary = min(300000, max(30000, int(answer)))
    q.answers['desired_salary'] = salary
    q.directly_asked_traits.add('desired_salary')
    q.questions_asked += 1
    q.fill_defaults()

    recommendations = get_recommendations_from_answers(q.answers)
    saved_path = save_response(
        session_id,
        q.answers,
        recommendations,
        source='web',
        questions_asked=int(q.questions_asked),
    )
    return JSONResponse(content={
        'done': True,
        'session_id': session_id,
        'recommendations': to_python(recommendations),
        'stats': {'questions_asked': int(q.questions_asked)},
        'data_saved': True,
        'data_file': str(saved_path),
    })


@app.post('/api/feedback')
async def submit_feedback(request: Request):
    try:
        data = await request.json()
        session_id = data.get('session_id')
        chosen_fields = data.get('chosen_fields') or []
        feedback_score = data.get('feedback_score')

        if not session_id or session_id not in sessions:
            return JSONResponse({'error': 'Сессия не найдена'}, status_code=404)

        path = update_labels(
            session_id,
            chosen_fields,
            feedback_score=feedback_score,
            label_source='self_report',
        )
        return JSONResponse({
            'ok': True,
            'message': 'Спасибо! Ваши ответы сохранены для улучшения сервиса.',
            'file': str(path),
        })
    except ValueError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)
    except Exception as exc:
        return JSONResponse({'error': str(exc)}, status_code=500)


@app.get('/api/directions')
async def list_directions():
    return JSONResponse({'directions': DUBNA_DIRECTION_KEYS})


async def get_next_question(session_id: str):
    session = sessions[session_id]
    q = session['questionnaire']

    if session.get('current_interest') is None:
        if session.get('pending_interests'):
            interest = session['pending_interests'].pop(0)
            session['current_interest'] = interest
            session['current_skill'] = q.SKILL_QUESTIONS[interest]['skill']
            session['current_q_idx'] = 0
            session['last_answer'] = None
        else:
            personal_traits = [
                'logical_thinking', 'memory_ability', 'problem_solving',
                'communication_skill', 'teamwork_skill',
            ]
            remaining = [t for t in personal_traits if t not in q.answers]
            if remaining:
                session['stage'] = 'personal'
                session['personal_traits'] = remaining
                session['personal_idx'] = 0
                trait = remaining[0]
                text = q.COMMON_TRAITS.get(trait, f'Оцените {trait}?')
                return JSONResponse({
                    'question': {'id': trait, 'text': text},
                    'progress': {
                        'stage': 'personal',
                        'current': 1,
                        'total': len(remaining),
                    },
                })
            session['stage'] = 'salary'
            return JSONResponse({
                'question': {
                    'id': 'salary',
                    'text': 'Какую желаемую зарплату (в рублях) вы ожидаете?',
                },
                'is_salary': True,
            })

    interest = session['current_interest']
    questions = q.SKILL_QUESTIONS[interest]['questions']
    current_idx = session.get('current_q_idx', 0)

    if current_idx > 0:
        last_answer = session.get('last_answer', 0)
        threshold = questions[current_idx - 1][1]
        if last_answer < threshold:
            session['current_interest'] = None
            return await get_next_question(session_id)

    if current_idx >= len(questions):
        session['current_interest'] = None
        return await get_next_question(session_id)

    q_text, _threshold = questions[current_idx]
    session['current_q_idx'] = current_idx + 1
    level_names = {0: 'Базовый', 1: 'Средний', 2: 'Продвинутый'}
    level_name = level_names.get(current_idx, f'Уровень {current_idx + 1}')
    return JSONResponse({
        'question': {
            'id': f'{interest}_q{current_idx}',
            'text': q_text,
            'context': f'Область: {interest} [{level_name}]',
        },
        'progress': {'stage': 'detailed'},
    })


def get_recommendations_from_answers(answers: Dict) -> List[Dict]:
    if not advisor.is_loaded:
        return [{
            'rank': 1,
            'field': 'Модель не загружена',
            'probability': 0,
            'match_level': 'ERROR',
            'explanation': 'Запустите python train_model.py',
            'description': '',
            'key_skills': '',
        }]

    import pandas as pd

    row = {trait: answers.get(trait, 3.0) for trait in EXPANDED_FEATURES}
    if 'desired_salary' in row:
        row['desired_salary'] = min(300000, max(30000, float(row['desired_salary'])))

    recommendations, _, _ = advisor.get_recommendations(pd.DataFrame([row]))
    return recommendations


def main():
    import os
    import uvicorn

    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '7777'))
    uvicorn.run('main:app', host=host, port=port, reload=False, log_level='info')


if __name__ == '__main__':
    main()
