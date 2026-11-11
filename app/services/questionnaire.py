"""Динамический движок опросника на конфигурации из БД.

Воспроизводит логику AdaptiveQuestionnaireV4, но вопросы, цепочки навыков
и пороги ветвления загружаются из PostgreSQL. Состояние сессии хранится
как JSON-словарь и переживает рестарты/несколько воркеров.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    CustomFormField,
    Feature,
    Question,
    QuestionGroup,
    QuestionType,
    UniversitySettings,
)

LEVEL_NAMES = {0: 'Базовый', 1: 'Средний', 2: 'Продвинутый'}
STAGE_TITLES = {
    'screening': 'Интересы',
    'detailed': 'Навыки',
    'personal': 'Общие качества',
    'salary': 'Зарплата',
    'ege_select': 'Выбор предметов ЕГЭ',
    'ege': 'Баллы ЕГЭ',
    'custom': 'Анкета',
}

# Карта кодов ege_* → понятные названия предметов
EGE_SUBJECT_LABELS = {
    'ege_math': 'Математика (профиль)',
    'ege_russian': 'Русский язык',
    'ege_informatics': 'Информатика и ИКТ',
    'ege_physics': 'Физика',
    'ege_chemistry': 'Химия',
    'ege_biology': 'Биология',
    'ege_social': 'Обществознание',
    'ege_history': 'История',
    'ege_foreign': 'Иностранный язык',
    'ege_literature': 'Литература',
    'ege_geography': 'География',
}

SALARY_MIN = 30000
SALARY_MAX = 300000


def _eval_activation(cond: Optional[dict], answers: dict) -> bool:
    """Проверка условия активации цепочки навыков."""
    if not cond:
        return False
    cond_type = cond.get('type')
    value = float(cond.get('value', 3))
    if cond_type == 'interest_ge':
        feature = cond.get('feature')
        return float(answers.get(feature, 0) or 0) >= value
    if cond_type == 'any_interest_ge':
        return any(
            float(answers.get(f, 0) or 0) >= value
            for f in cond.get('features', [])
        )
    return False


class SurveyEngine:
    """Состояние сессии хранится в JSON-словаре state.

    Схема state:
        stage: screening|detailed|personal|salary|custom|done
        screening_idx: int
        pending_chains: list[chain_key]
        current_chain: chain_key|None
        chain_q_ids: list[int]
        chain_q_idx: int
        last_answer: float|None
        personal_idx: int
        answers: dict[feature_code, value]
        directly_asked: list[str]
        questions_asked: int
    """

    def __init__(self, db: Session):
        self.db = db
        self.features_by_id: dict[int, Feature] = {}
        self.features_by_code: dict[str, Feature] = {}
        self.screening: list[Question] = []
        self.chains: list[dict] = []
        self.personal: list[Question] = []
        self.salary: Optional[Question] = None
        self.ege_features: list[Feature] = []
        self.custom_fields: list[CustomFormField] = []
        self.custom_at_start: bool = True
        self._questions: dict[int, Question] = {}
        self._load()

    # --- загрузка конфигурации из БД ---

    def _load(self) -> None:
        features = self.db.scalars(
            select(Feature)
            .where(Feature.is_active)
            .order_by(Feature.sort_order)
        ).all()
        for f in features:
            self.features_by_id[f.id] = f
            self.features_by_code[f.code] = f

        groups = {
            g.code.value: g
            for g in self.db.scalars(select(QuestionGroup)).all()
        }
        group_ids = {g.id for g in groups.values()}

        questions = self.db.scalars(
            select(Question)
            .where(Question.is_active)
            .options(selectinload(Question.group), selectinload(Question.feature))
            .order_by(Question.id)
        ).all()

        for q in questions:
            if q.group_id not in group_ids:
                continue
            self._questions[q.id] = q

        self.screening = [
            q for q in questions
            if q.group.code.value == 'screening'
        ]
        self.screening.sort(key=lambda q: (q.sort_order, q.id))

        self.personal = [
            q for q in questions
            if q.group.code.value == 'personal'
        ]
        self.personal.sort(key=lambda q: (q.sort_order, q.id))

        salary_qs = [q for q in questions if q.group.code.value == 'salary']
        self.salary = salary_qs[0] if salary_qs else None

        # цепочки навыков: группируем по feature_id (все вопросы цепочки
        # пишутся в один признак и имеют одинаковое activation_condition)
        chains_map: dict[int, dict] = {}
        for q in questions:
            if q.group.code.value != 'detailed' or q.feature_id is None:
                continue
            chain = chains_map.setdefault(q.feature_id, {
                'key': q.feature_id,
                'questions': [],
                'activation': q.activation_condition,
            })
            chain['questions'].append(q)
        for chain in chains_map.values():
            chain['questions'].sort(key=lambda q: q.level)
            chain['key'] = chain['questions'][0].feature.code
        self.chains = list(chains_map.values())

        self.ege_features = [
            f for f in features
            if f.code.startswith('ege_') and f.data_type.value in ('number', 'rating_1_5')
        ]
        self.ege_features.sort(key=lambda f: f.sort_order)

        self.custom_fields = self.db.scalars(
            select(CustomFormField)
            .where(CustomFormField.is_active)
            .order_by(CustomFormField.sort_order)
        ).all()

        settings_row = self.db.scalar(
            select(UniversitySettings).order_by(UniversitySettings.id).limit(1),
        )
        self.custom_at_start = (
            settings_row is None
            or settings_row.custom_form_position != 'end'
        )

    # --- состояние ---

    @staticmethod
    def start_state() -> dict:
        return {
            'stage': 'screening',
            'screening_idx': 0,
            'pending_chains': [],
            'current_chain': None,
            'chain_q_ids': [],
            'chain_q_idx': 0,
            'last_answer': None,
            'personal_idx': 0,
            'answers': {},
            'directly_asked': [],
            'questions_asked': 0,
        }

    # --- генерация payload ---

    def first_payload(self, state: dict) -> dict:
        if self.custom_fields and self.custom_at_start:
            state['stage'] = 'custom'
            return self.custom_payload(state)
        return self._first_screening_payload(state)

    def _first_screening_payload(self, state: dict) -> dict:
        if not self.screening:
            # нет вопросов — сразу зарплата
            state['stage'] = 'salary'
            return self._salary_payload()
        state['stage'] = 'screening'
        state['screening_idx'] = 0
        return self._payload(self.screening[0], state)

    def after_custom_payload(self, state: dict) -> dict:
        """Продолжение после стартовой анкеты вуза."""
        return self._first_screening_payload(state)

    def _payload(self, q: Question, state: dict, chain_context: bool = False) -> dict:
        payload: dict[str, Any] = {
            'id': str(q.id),
            'text': q.text,
            'image_url': q.image_url,
            'type': q.question_type.value,
            'options': q.options,
        }
        if chain_context and q.feature_id is not None:
            feat = self.features_by_id.get(q.feature_id)
            level_name = LEVEL_NAMES.get(q.level, f'Уровень {q.level}')
            payload['context'] = (
                f'Область: {feat.label if feat else "?"} [{level_name}]'
            )

        gcode = q.group.code.value
        if gcode == 'screening':
            payload['progress'] = {
                'stage': 'screening',
                'title': STAGE_TITLES['screening'],
                'current': state['screening_idx'] + 1,
                'total': len(self.screening),
            }
        elif gcode == 'detailed':
            payload['progress'] = {
                'stage': 'detailed',
                'title': STAGE_TITLES['detailed'],
                'current': state['chain_q_idx'] + 1,
                'total': len(state['chain_q_ids']),
            }
        elif gcode == 'personal':
            payload['progress'] = {
                'stage': 'personal',
                'title': STAGE_TITLES['personal'],
                'current': state['personal_idx'] + 1,
                'total': len(self.personal),
            }
        return payload

    def _salary_payload(self) -> dict:
        return {
            'id': 'salary',
            'text': (
                self.salary.text
                if self.salary
                else 'Какую желаемую зарплату (в рублях) вы ожидаете?'
            ),
            'type': 'salary',
            'is_salary': True,
            'progress': {'stage': 'salary', 'title': STAGE_TITLES['salary']},
        }

    def custom_payload(self, state: dict) -> dict:
        return {
            'id': 'custom',
            'text': 'Заполните анкету — вуз сможет связаться с вами',
            'type': 'form',
            'is_custom': True,
            'fields': [self._field_payload(f) for f in self.custom_fields],
            'progress': {'stage': 'custom', 'title': STAGE_TITLES['custom']},
        }

    def _ege_select_payload(self, state: dict) -> dict:
        """Показывает чекбоксы для выбора предметов ЕГЭ перед вводом баллов."""
        return {
            'id': 'ege_select',
            'text': 'Какие ЕГЭ вы сдавали? (отметьте нужное)',
            'type': 'checkbox_multi',
            'is_ege_select': True,
            'subjects': [
                {'code': code, 'label': label}
                for code, label in EGE_SUBJECT_LABELS.items()
                if code in {f.code for f in self.ege_features}
            ],
            'progress': {'stage': 'ege_select', 'title': STAGE_TITLES['ege_select']},
        }

    def _ege_payload(self, state: dict) -> dict:
        selected = state.get('ege_selected', [])
        return {
            'id': 'ege',
            'text': (
                'Укажите ваши баллы ЕГЭ по выбранным предметам'
            ),
            'type': 'ege',
            'is_ege': True,
            'subjects': [
                {'code': f.code, 'label': f.label}
                for f in self.ege_features
                if f.code in selected
            ],
            'progress': {'stage': 'ege', 'title': STAGE_TITLES['ege']},
        }

    @staticmethod
    def _field_payload(f: CustomFormField) -> dict:
        return {
            'code': f.code,
            'label': f.label,
            'field_type': f.field_type.value,
            'options': f.options,
            'required': f.required,
            'description': getattr(f, 'description', '') or '',
            'examples': getattr(f, 'examples', None) or [],
        }

    # --- обработка ответов ---

    def submit_answer(self, state: dict, question_id: str, answer: Any):
        """Применяет ответ и возвращает (payload следующего вопроса | None, state).

        None означает «опрос завершён» (или нужно перейти к анкете custom —
        в этом случае payload имеет is_custom=True).
        """
        if question_id == 'salary':
            state['answers']['desired_salary'] = self._clamp_salary(answer)
            state['directly_asked'].append('desired_salary')
            state['questions_asked'] += 1
            if self.ege_features:
                state['stage'] = 'ege_select'
                return self._ege_select_payload(state), state
            # анкета в конце — показываем; анкета в начале уже собрана
            if self.custom_fields and not self.custom_at_start:
                state['stage'] = 'custom'
                return self.custom_payload(state), state
            return None, state

        if question_id == 'ege_select':
            """Сохраняет выбранные предметы ЕГЭ и переходит к вводу баллов."""
            selected = answer if isinstance(answer, list) else []
            # Фильтруем: только коды из ege_features
            valid_codes = {f.code for f in self.ege_features}
            state['ege_selected'] = [c for c in selected if c in valid_codes]
            state['questions_asked'] += 1
            state['stage'] = 'ege'
            return self._ege_payload(state), state

        if question_id == 'ege':
            return self._submit_ege(state, answer), state

        qid = int(question_id)
        q = self._questions.get(qid)
        if q is None:
            raise ValueError(f'Вопрос {question_id} не найден или неактивен')
        if q.feature is None:
            raise ValueError(f'Вопрос {question_id} не привязан к признаку')

        code = q.feature.code
        state['answers'][code] = self._coerce_answer(q, answer)
        if code not in state['directly_asked']:
            state['directly_asked'].append(code)
        state['questions_asked'] += 1
        state['last_answer'] = float(answer)

        gcode = q.group.code.value

        if gcode == 'screening':
            state['screening_idx'] += 1
            if state['screening_idx'] >= len(self.screening):
                state['pending_chains'] = self._compute_pending_chains(
                    state['answers'],
                )
                return self._enter_detailed(state), state
            return self._payload(self.screening[state['screening_idx']], state), state

        if gcode == 'detailed':
            idx = state['chain_q_idx']
            qids = state['chain_q_ids']
            if idx + 1 < len(qids):
                nxt = self._questions.get(qids[idx + 1])
                if nxt is not None and float(answer) >= (nxt.threshold or 1.0):
                    state['chain_q_idx'] = idx + 1
                    return self._payload(nxt, state, chain_context=True), state
            return self._enter_detailed(state), state

        if gcode == 'personal':
            state['personal_idx'] += 1
            if state['personal_idx'] >= len(self.personal):
                return self._salary_payload(), state
            return self._payload(self.personal[state['personal_idx']], state), state

        return None, state

    # --- переходы между этапами ---

    def _enter_detailed(self, state: dict):
        if state['pending_chains']:
            chain_key = state['pending_chains'].pop(0)
            chain = self._chain_by_key(chain_key)
            if chain is None:
                return self._enter_detailed(state)
            state['stage'] = 'detailed'
            state['current_chain'] = chain_key
            state['chain_q_ids'] = [q.id for q in chain['questions']]
            state['chain_q_idx'] = 0
            state['last_answer'] = None
            return self._payload(chain['questions'][0], state, chain_context=True)

        # цепочки закончились → общие качества
        state['stage'] = 'personal'
        state['personal_idx'] = 0
        while (
            state['personal_idx'] < len(self.personal)
            and self.personal[state['personal_idx']].feature is not None
            and self.personal[state['personal_idx']].feature.code in state['answers']
        ):
            state['personal_idx'] += 1
        if state['personal_idx'] >= len(self.personal):
            return self._salary_payload()
        return self._payload(self.personal[state['personal_idx']], state)

    def _chain_by_key(self, key: str) -> Optional[dict]:
        for chain in self.chains:
            if chain['key'] == key:
                return chain
        return None

    def _compute_pending_chains(self, answers: dict) -> list:
        return [
            chain['key']
            for chain in self.chains
            if _eval_activation(chain['activation'], answers)
        ]

    # --- финализация ---

    def build_profile(self, state: dict) -> dict:
        """Собирает полный профиль: ответы + значения по умолчанию.
        
        Несданные ЕГЭ-предметы не добавляются в профиль — подставляется default_value.
        """
        profile: dict[str, Any] = {}
        features = sorted(
            self.features_by_code.values(),
            key=lambda f: f.sort_order,
        )
        for feat in features:
            code = feat.code
            if code in state['answers']:
                value = state['answers'][code]
            else:
                value = feat.default_value
            profile[code] = self._coerce_feature(feat, value)
        return profile

    @staticmethod
    def _coerce_answer(q: Question, answer: Any) -> Any:
        if q.question_type in (QuestionType.rating_1_5, QuestionType.number_input):
            return float(answer)
        if q.question_type == QuestionType.salary:
            return int(answer)
        return answer

    @staticmethod
    def _coerce_feature(feat: Feature, value: Any) -> Any:
        if feat.data_type.value in ('salary', 'number'):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return 0
        if feat.data_type.value == 'rating_1_5':
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
        return str(value)

    @staticmethod
    def _clamp_salary(answer: Any) -> int:
        try:
            value = int(float(answer))
        except (TypeError, ValueError):
            value = 100000
        return max(SALARY_MIN, min(SALARY_MAX, value))

    def _submit_ege(self, state: dict, answer: Any) -> Optional[dict]:
        """Сохраняет баллы ЕГЭ: выбранные — по баллам, несданные — не добавляются в answers."""
        selected = state.get('ege_selected', [])
        values = answer if isinstance(answer, dict) else {}

        for f in self.ege_features:
            code = f.code
            if code in selected:
                # Сданный предмет — берём балл
                try:
                    score = int(float(values.get(code)))
                except (TypeError, ValueError):
                    score = 0
                score = max(0, min(100, score))
                state['answers'][code] = score
                if code not in state['directly_asked']:
                    state['directly_asked'].append(code)
            # Несданные предметы не добавляются в answers — они просто отсутствуют в профиле

        state['questions_asked'] += 1
        state['last_answer'] = None

        # после ЕГЭ — финиш (зарплата уже введена до ЕГЭ)
        state['stage'] = 'done'
        return None