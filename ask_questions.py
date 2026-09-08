#!/usr/bin/env python3
"""
@file ask_questions.py
@brief Адаптивный опросник - 19 НАПРАВЛЕНИЙ (опрос по интересам)
@version 12.0
"""

import sys
import csv
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List, Tuple

import warnings

from config.model_config import EXPANDED_FEATURES

warnings.filterwarnings('ignore')


class AdaptiveQuestionnaireV4:
    def __init__(self):
        self.interests = {}
        self.answers = {}
        self.questions_asked = 0
        self.directly_asked_traits: Set[str] = set()

        self.ALL_TRAITS = list(EXPANDED_FEATURES)

        # 19 вопросов про реальные интересы
        self.SCREENING_QUESTIONS: List[Tuple[str, str]] = [
            ('chemical_analysis', 'Химия, работа с веществами, лабораторные исследования'),
            ('experimental_physics', 'Физика, изучение законов природы, эксперименты'),
            ('ecology', 'Экология, охрана природы, окружающая среда'),
            ('computer_systems', 'Компьютеры, сети, IT-инфраструктура'),
            ('software_development', 'Программирование, создание сайтов и приложений'),
            ('business_analytics', 'Бизнес, аналитика данных, IT в бизнесе'),
            ('electronics', 'Электроника, конструирование устройств, схемотехника'),
            ('power_engineering', 'Энергетика, электричество, генерация энергии'),
            ('nuclear_physics', 'Ядерная физика, атом, радиация, реакторы'),
            ('automation_tech', 'Автоматизация, роботы, производство'),
            ('aerospace_design', 'Авиация, ракеты, самолёты, космос'),
            ('psychological_counseling', 'Психология, помощь людям, консультирование'),
            ('management', 'Управление компаниями, руководство, бизнес'),
            ('public_administration', 'Государство, работа в министерствах, управление регионами'),
            ('social_research', 'Социология, изучение общества, опросы, исследования'),
            ('legal_knowledge', 'Право, юриспруденция, законы, документы'),
            ('linguistics_skill', 'Иностранные языки, перевод, лингвистика'),
            ('math_modeling', 'Математика, математическое моделирование, анализ данных'),
            ('algorithms_theory', 'Алгоритмы, структуры данных, олимпиадное программирование'),
        ]

        self.SKILL_QUESTIONS = {
            'software_development': {
                'skill': 'software_development',
                'questions': [
                    ('Вы знаете основы программирования?', 2.0),
                    ('Можете написать программу на Python/Java/C++?', 3.0),
                    ('Создавали свои проекты или работали в команде?', 4.0)
                ]
            },
            'computer_systems': {
                'skill': 'computer_systems',
                'questions': [
                    ('Понимаете, как устроен компьютер?', 2.0),
                    ('Можете собрать ПК или настроить ОС?', 3.0),
                    ('Разбираетесь в компьютерных сетях?', 4.0)
                ]
            },
            'it_infrastructure': {
                'skill': 'it_infrastructure',
                'questions': [
                    ('Знаете, что такое серверы и облачные технологии?', 2.0),
                    ('Настраивали сети или серверное ПО?', 3.0),
                    ('Работали с системами виртуализации (Docker, VMware)?', 4.0)
                ]
            },
            'algorithms_theory': {
                'skill': 'algorithms_theory',
                'questions': [
                    ('Знаете основные алгоритмы (сортировка, поиск)?', 2.0),
                    ('Можете оценить сложность алгоритма?', 3.0),
                    ('Решали олимпиадные задачи по программированию?', 4.0)
                ]
            },
            'math_modeling': {
                'skill': 'math_modeling',
                'questions': [
                    ('Умеете решать сложные уравнения?', 2.0),
                    ('Можете построить математическую модель для реальной задачи?', 3.0),
                    ('Использовали MATLAB, Wolfram Mathematica или Python для моделирования?', 4.0)
                ]
            },
            'experimental_physics': {
                'skill': 'experimental_physics',
                'questions': [
                    ('Понимаете основные физические законы?', 2.0),
                    ('Можете решать задачи по физике?', 3.0),
                    ('Проводили физические эксперименты в лаборатории?', 4.0)
                ]
            },
            'nuclear_physics': {
                'skill': 'nuclear_physics',
                'questions': [
                    ('Интересуетесь устройством атома и радиоактивностью?', 2.0),
                    ('Понимаете принципы работы ядерного реактора?', 3.0),
                    ('Изучали ядерную физику или работали с дозиметрией?', 4.0)
                ]
            },
            'chemical_analysis': {
                'skill': 'chemical_analysis',
                'questions': [
                    ('Знаете основные химические реакции?', 2.0),
                    ('Проводили химические опыты в лаборатории?', 3.0),
                    ('Углублённо изучали химию (органическую, неорганическую)?', 4.0)
                ]
            },
            'economic_analysis': {
                'skill': 'economic_analysis',
                'questions': [
                    ('Интересуетесь финансами и экономикой?', 2.0),
                    ('Можете проанализировать финансовые показатели компании?', 3.0),
                    ('Управляли бюджетом или пробовали себя в бизнесе?', 4.0)
                ]
            },
            'psychological_counseling': {
                'skill': 'psychological_counseling',
                'questions': [
                    ('Интересно понимать поведение и мотивы людей?', 2.0),
                    ('Умеете слушать и помогать людям решать проблемы?', 3.0),
                    ('Изучали психологию или работали с людьми?', 4.0)
                ]
            },
            'linguistics_skill': {
                'skill': 'linguistics_skill',
                'questions': [
                    ('Интересно изучать иностранные языки?', 2.0),
                    ('Можете общаться на иностранном языке?', 3.0),
                    ('Свободно владеете одним или несколькими языками?', 4.0)
                ]
            },
            'legal_knowledge': {
                'skill': 'legal_knowledge',
                'questions': [
                    ('Интересуетесь законами и правовой системой?', 2.0),
                    ('Можете проанализировать юридический документ?', 3.0),
                    ('Участвовали в дебатах, олимпиадах по праву?', 4.0)
                ]
            },
            'social_research': {
                'skill': 'social_research',
                'questions': [
                    ('Интересно изучать общество и социальные процессы?', 2.0),
                    ('Умеете анализировать данные опросов и статистику?', 3.0),
                    ('Проводили социологические исследования?', 4.0)
                ]
            },
            'business_analytics': {
                'skill': 'business_analytics',
                'questions': [
                    ('Интересуетесь IT в бизнесе и автоматизацией?', 2.0),
                    ('Понимаете, как автоматизировать бизнес-процессы?', 3.0),
                    ('Работали с CRM, ERP или системами бизнес-аналитики?', 4.0)
                ]
            },
            'ecology': {
                'skill': 'ecology',
                'questions': [
                    ('Интересуетесь экологией и охраной природы?', 2.0),
                    ('Понимаете экологические процессы и проблемы?', 3.0),
                    ('Участвовали в экологических проектах или волонтёрстве?', 4.0)
                ]
            },
            'electronics': {
                'skill': 'electronics',
                'questions': [
                    ('Интересуетесь электроникой и схемами?', 2.0),
                    ('Можете собрать электронную схему по схемотехнике?', 3.0),
                    ('Разрабатывали электронные устройства (Arduino, Raspberry Pi)?', 4.0)
                ]
            },
            'management': {
                'skill': 'management',
                'questions': [
                    ('Интересуетесь управлением и лидерством?', 2.0),
                    ('Руководили проектами или командой людей?', 3.0),
                    ('Управляли бюджетом или ресурсами организации?', 4.0)
                ]
            },
            'public_administration': {
                'skill': 'public_administration',
                'questions': [
                    ('Интересуетесь государственным управлением?', 2.0),
                    ('Понимаете, как работают государственные органы?', 3.0),
                    ('Участвовали в общественных проектах или работали с госструктурами?', 4.0)
                ]
            },
            'power_engineering': {
                'skill': 'power_engineering',
                'questions': [
                    ('Интересуетесь электроэнергетикой?', 2.0),
                    ('Понимаете принципы работы генераторов и трансформаторов?', 3.0),
                    ('Изучали электрические сети или возобновляемую энергетику?', 4.0)
                ]
            },
            'automation_tech': {
                'skill': 'automation_tech',
                'questions': [
                    ('Интересуетесь автоматизацией производства?', 2.0),
                    ('Понимаете принципы работы ПЛК (программируемых логических контроллеров)?', 3.0),
                    ('Разрабатывали системы автоматизации или работали с промышленными роботами?', 4.0)
                ]
            },
            'aerospace_design': {
                'skill': 'aerospace_design',
                'questions': [
                    ('Интересуетесь устройством самолётов, ракет и космических аппаратов?', 2.0),
                    ('Понимаете основы аэродинамики?', 3.0),
                    ('Работали с CAD/CAE системами (SolidWorks, Компас, Catia)?', 4.0)
                ]
            },
        }

        self.COMMON_TRAITS = {
            'logical_thinking': 'Как вы оцениваете своё логическое мышление?',
            'memory_ability': 'Как вы оцениваете свою память?',
            'problem_solving': 'Как вы оцениваете свои навыки решения сложных задач?',
            'communication_skill': 'Как вы оцениваете свою коммуникабельность?',
            'teamwork_skill': 'Как вы оцениваете свою способность работать в команде?',
        }

        personal_traits = {
            'logical_thinking', 'memory_ability', 'problem_solving',
            'communication_skill', 'teamwork_skill',
        }
        self.DEFAULT_VALUES = {}
        for trait in EXPANDED_FEATURES:
            if trait == 'desired_salary':
                self.DEFAULT_VALUES[trait] = 100000
            elif trait in personal_traits:
                self.DEFAULT_VALUES[trait] = 3.0
            else:
                self.DEFAULT_VALUES[trait] = 2.5

    def ask_rating(self, text: str, trait: str = None) -> int:
        print(f"\n   {text}")
        print("   1 - совсем не интересую / очень низкий")
        print("   2 - слабый интерес / ниже среднего")
        print("   3 - средний интерес / средний уровень")
        print("   4 - интересно / выше среднего")
        print("   5 - очень интересно / высокий уровень")

        while True:
            try:
                answer = input("   Ваша оценка (1-5): ")
                value = int(answer)
                if 1 <= value <= 5:
                    if trait:
                        self.directly_asked_traits.add(trait)
                    return value
                print("   Введите число от 1 до 5")
            except ValueError:
                print("   Введите число от 1 до 5")

    def ask_salary(self) -> int:
        print("\n   Какую желаемую зарплату (в рублях) вы ожидаете?")
        while True:
            try:
                answer = input("   -> ")
                value = max(30000, min(300000, int(answer)))
                value = round(value, -3)
                print(f"   Принято: {value:,} руб.")
                self.directly_asked_traits.add('desired_salary')
                return value
            except ValueError:
                print("   Введите число")

    def ask_skill_adaptive(self, trait: str, questions_list: list) -> float:
        answers = []
        for i, (q_text, threshold) in enumerate(questions_list):
            if i == 0:
                print(f"\n   [Базовый уровень] {q_text}")
                answer = self.ask_rating(q_text, trait=trait)
                self.questions_asked += 1
                answers.append(answer)
                continue
            prev_answer = answers[-1]
            if prev_answer >= threshold:
                level_name = "Средний уровень" if i == 1 else "Продвинутый уровень"
                print(f"\n   [{level_name}] {q_text}")
                answer = self.ask_rating(q_text, trait=trait)
                self.questions_asked += 1
                answers.append(answer)
            else:
                print(f"\n   [!] Вопросы по этой сфере закончены (предыдущий ответ {prev_answer} < {threshold})")
                break
        return float(answers[-1]) if answers else 1.0

    def screening(self):
        print("\n" + "=" * 70)
        print("[ШАГ 1] ОПРЕДЕЛЕНИЕ ИНТЕРЕСОВ")
        print("Оцените, насколько вам интересны следующие сферы:")
        print("=" * 70)

        for trait, name in self.SCREENING_QUESTIONS:
            score = self.ask_rating(f"{name}?", trait=trait)
            self.interests[trait] = score
            self.answers[trait] = score
            self.questions_asked += 1

    def detailed_by_interest(self):
        print("\n" + "=" * 70)
        print("[ШАГ 2] УГЛУБЛЁННЫЕ ВОПРОСЫ ПО НАВЫКАМ")
        print("=" * 70)

        # Основные интересы
        for interest_trait, score in self.interests.items():
            if score >= 3 and interest_trait in self.SKILL_QUESTIONS:
                skill_info = self.SKILL_QUESTIONS[interest_trait]
                skill_trait = skill_info['skill']
                questions = skill_info['questions']
                print(f"\n--- {interest_trait.upper()} ---")
                skill_value = self.ask_skill_adaptive(skill_trait, questions)
                self.answers[skill_trait] = skill_value

        # Дополнительные признаки - принудительная активация через интересы
        # it_infrastructure активируется при интересе к computer_systems
        if self.interests.get('computer_systems', 0) >= 3:
            if 'it_infrastructure' not in self.answers:
                if 'it_infrastructure' in self.SKILL_QUESTIONS:
                    print(f"\n--- IT_INFRASTRUCTURE (дополнительно) ---")
                    skill_value = self.ask_skill_adaptive('it_infrastructure', self.SKILL_QUESTIONS['it_infrastructure']['questions'])
                    self.answers['it_infrastructure'] = skill_value

        # economic_analysis активируется при интересе к business_analytics или management
        if self.interests.get('business_analytics', 0) >= 3 or self.interests.get('management', 0) >= 3:
            if 'economic_analysis' not in self.answers:
                if 'economic_analysis' in self.SKILL_QUESTIONS:
                    print(f"\n--- ECONOMIC_ANALYSIS (дополнительно) ---")
                    skill_value = self.ask_skill_adaptive('economic_analysis', self.SKILL_QUESTIONS['economic_analysis']['questions'])
                    self.answers['economic_analysis'] = skill_value

        print("\n--- ОБЩИЕ НАВЫКИ ---")
        additional_to_ask = [
            'logical_thinking', 'memory_ability', 'problem_solving',
            'communication_skill', 'teamwork_skill'
        ]
        for trait in additional_to_ask:
            if trait not in self.answers:
                q_text = self.COMMON_TRAITS.get(trait, f"Оцените {trait}?")
                answer = self.ask_rating(q_text, trait=trait)
                self.answers[trait] = answer
                self.questions_asked += 1

    def fill_defaults(self):
        for trait in self.ALL_TRAITS:
            if trait not in self.answers:
                self.answers[trait] = self.DEFAULT_VALUES.get(trait, 3.0)

    def run(self) -> Dict[str, float]:
        print("\n" + "=" * 70)
        print("ПРОФОРИЕНТАЦИОННЫЙ ОПРОСНИК")
        print("Университет 'Дубна' — выбор направления обучения")
        print("=" * 70)
        self.screening()
        self.detailed_by_interest()
        print("\n" + "=" * 70)
        print("[ШАГ 3] КАРЬЕРНЫЕ ОЖИДАНИЯ")
        print("=" * 70)
        self.answers['desired_salary'] = self.ask_salary()
        self.questions_asked += 1
        self.fill_defaults()

        valid_traits = [t for t in self.directly_asked_traits if t in self.ALL_TRAITS]
        directly_answered = len(valid_traits)

        print("\n" + "=" * 70)
        print("ОПРОС ЗАВЕРШЁН")
        print("=" * 70)
        print(f"   Получено ответов: {directly_answered}")
        print(f"   Всего задано вопросов: {self.questions_asked}")
        return self.answers

    def get_stats(self) -> Dict:
        valid_traits = [t for t in self.directly_asked_traits if t in self.ALL_TRAITS]
        return {
            'directly_asked': len(valid_traits),
            'defaults_used': len(self.ALL_TRAITS) - len(valid_traits),
            'total_questions': self.questions_asked,
            'total_features': len(self.ALL_TRAITS)
        }


def save_profile_to_csv(profile: Dict[str, float], output_path: str = None) -> str:
    feature_order = list(EXPANDED_FEATURES)
    Path('profiles').mkdir(exist_ok=True)
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'profiles/student_{timestamp}.csv'
    else:
        output_path = f'profiles/{output_path}'
        if not output_path.endswith('.csv'):
            output_path += '.csv'

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(feature_order)
        writer.writerow([profile.get(trait, 3.0) for trait in feature_order])
    print(f"\n[+] Профиль сохранён: {output_path}")
    return output_path


def show_profile_summary(profile: Dict[str, float]):
    print("\n" + "=" * 70)
    print("ВАШ ПРОФИЛЬ НАВЫКОВ")
    print("=" * 70)

    key_traits = [
        ('software_development', 'Программирование'),
        ('computer_systems', 'Компьютерные системы'),
        ('it_infrastructure', 'IT-инфраструктура'),
        ('algorithms_theory', 'Алгоритмы'),
        ('math_modeling', 'Матмоделирование'),
        ('experimental_physics', 'Физика'),
        ('nuclear_physics', 'Ядерная физика'),
        ('chemical_analysis', 'Химия'),
        ('economic_analysis', 'Экономика'),
        ('psychological_counseling', 'Психология'),
        ('linguistics_skill', 'Лингвистика'),
        ('legal_knowledge', 'Юриспруденция'),
        ('social_research', 'Социология'),
        ('business_analytics', 'Бизнес-аналитика'),
        ('ecology', 'Экология'),
        ('electronics', 'Электроника'),
        ('management', 'Менеджмент'),
        ('public_administration', 'Госуправление'),
        ('power_engineering', 'Энергетика'),
        ('automation_tech', 'Автоматизация'),
        ('aerospace_design', 'Авиастроение'),
        ('logical_thinking', 'Логика'),
        ('memory_ability', 'Память'),
        ('problem_solving', 'Решение задач'),
        ('communication_skill', 'Коммуникация'),
        ('teamwork_skill', 'Работа в команде'),
    ]

    for trait, name in key_traits:
        if trait in profile:
            value = profile[trait]
            bar = "█" * int(value) + "░" * (5 - int(value))
            print(f"   {name:25}: {value:.1f} {bar}")

    salary = profile.get('desired_salary', 0)
    print(f"\n   {'Желаемая зарплата':25}: {salary:,.0f} руб.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', type=str, default=None)
    parser.add_argument('--quiet', '-q', action='store_true')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("АДАПТИВНЫЙ ПРОФОРИЕНТАЦИОННЫЙ ОПРОСНИК v12.0")
    print("Университет 'Дубна'")
    print("=" * 70)

    questionnaire = AdaptiveQuestionnaireV4()
    profile = questionnaire.run()

    if not args.quiet:
        show_profile_summary(profile)

    csv_path = save_profile_to_csv(profile, args.output)
    print(f"\n Профиль сохранён: {csv_path}")
    print(f"   Запустите веб-сервер (python main.py) для получения рекомендаций")


if __name__ == "__main__":
    main()