#!/usr/bin/env python3
"""Генерация синтетических данных и обучение multilabel-модели CareerAI."""

import json
import random
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from tensorflow import keras
from tensorflow.keras import layers

from config.model_config import (
    DIRECTION_KEY_SKILLS,
    DUBNA_DIRECTION_KEYS,
    EXPANDED_FEATURES,
    MODEL_DIR,
)

warnings.filterwarnings('ignore')

np.random.seed(42)
tf.random.set_seed(42)
random.seed(42)


def generate_training_data():
    print(f'Generating training data for {len(DUBNA_DIRECTION_KEYS)} directions...')
    data = []
    multi_labels = []

    for _ in range(100):
        profile = {f: 5.0 for f in EXPANDED_FEATURES}
        profile['desired_salary'] = 300000
        profile['chosen_fields'] = DUBNA_DIRECTION_KEYS.copy()
        data.append(profile)
        multi_labels.append(profile['chosen_fields'])

    neutral_traits = [
        'logical_thinking', 'memory_ability', 'problem_solving',
        'communication_skill', 'teamwork_skill',
    ]

    for direction, key_skills in DIRECTION_KEY_SKILLS.items():
        for _ in range(150):
            profile = {}
            for feature in EXPANDED_FEATURES:
                if feature in key_skills:
                    profile[feature] = 5.0
                elif feature in neutral_traits:
                    profile[feature] = 2.5
                else:
                    profile[feature] = 2.5
            profile['desired_salary'] = float(np.random.choice([80000, 100000, 120000]))
            profile['chosen_fields'] = [direction]
            data.append(profile)
            multi_labels.append(profile['chosen_fields'])

    for _ in range(1500):
        profile = {f: 1.0 for f in EXPANDED_FEATURES}
        num_dirs = int(np.random.choice([3, 4, 5, 6]))
        selected_dirs = np.random.choice(DUBNA_DIRECTION_KEYS, size=num_dirs, replace=False)
        for direction in selected_dirs:
            for skill in DIRECTION_KEY_SKILLS[direction]:
                profile[skill] = 5.0
        for feature in ['logical_thinking', 'memory_ability', 'problem_solving']:
            profile[feature] = float(np.random.uniform(3.0, 4.5))
        profile['desired_salary'] = float(np.random.choice([100000, 150000, 200000]))
        profile['chosen_fields'] = selected_dirs.tolist()
        data.append(profile)
        multi_labels.append(profile['chosen_fields'])

    for _ in range(1000):
        profile = {f: float(np.random.uniform(2.0, 4.5)) for f in EXPANDED_FEATURES}
        profile['desired_salary'] = float(np.random.choice([60000, 80000, 100000]))

        scores = {}
        for direction, key_skills in DIRECTION_KEY_SKILLS.items():
            skill_scores = [profile.get(skill, 0) for skill in key_skills]
            avg_score = float(np.mean(skill_scores))
            if avg_score >= 4:
                scores[direction] = avg_score

        if not scores:
            chosen = np.random.choice(
                DUBNA_DIRECTION_KEYS,
                size=int(np.random.choice([1, 2])),
                replace=False,
            ).tolist()
        else:
            chosen = list(scores.keys())[:3]
        profile['chosen_fields'] = chosen
        data.append(profile)
        multi_labels.append(profile['chosen_fields'])

    print('   Adding balancing samples...')
    balancing_cases = [
        ('Химия', ['chemical_analysis'], ['experimental_physics', 'nuclear_physics']),
        ('Физика', ['experimental_physics'], ['chemical_analysis', 'nuclear_physics', 'aerospace_design']),
        ('Химия, физика и механика материалов', ['chemical_analysis', 'experimental_physics'], []),
        ('Ядерные физика и технологии', ['nuclear_physics', 'experimental_physics'], ['chemical_analysis']),
        ('Экология и природопользование', ['ecology'], ['chemical_analysis']),
        ('Авиастроение', ['aerospace_design', 'experimental_physics'], ['chemical_analysis']),
        ('Информатика и вычислительная техника', ['computer_systems'], ['software_development']),
        ('Программная инженерия', ['software_development'], ['computer_systems']),
        ('Прикладная информатика', ['business_analytics'], ['computer_systems']),
        ('Конструирование и технология электронных средств', ['electronics'], ['computer_systems']),
        ('Электроэнергетика и электротехника', ['power_engineering'], ['experimental_physics']),
        ('Автоматизация технологических процессов', ['automation_tech', 'computer_systems'], []),
        ('Психология', ['psychological_counseling'], ['social_research']),
        ('Социология', ['social_research'], ['psychological_counseling']),
        ('Лингвистика', ['linguistics_skill'], ['psychological_counseling']),
        ('Юриспруденция', ['legal_knowledge'], ['economic_analysis']),
        ('Менеджмент', ['management'], ['economic_analysis']),
        ('Государственное и муниципальное управление', ['public_administration'], ['management']),
        (
            'Информационные системы и технологии',
            ['computer_systems', 'it_infrastructure', 'business_analytics'],
            [],
        ),
    ]

    for direction, required_skills, extra_skills in balancing_cases:
        for _ in range(200):
            profile = {f: 2.5 for f in EXPANDED_FEATURES}
            for skill in required_skills + extra_skills:
                profile[skill] = 5.0
            profile['desired_salary'] = float(np.random.choice([80000, 100000, 120000]))
            profile['chosen_fields'] = [direction]
            data.append(profile)
            multi_labels.append([direction])

    df = pd.DataFrame(data)
    Path('data').mkdir(exist_ok=True)
    df.to_csv('data/training_data.csv', index=False)

    print(f'\nTotal samples: {len(df)}')
    print(f'Features: {len(EXPANDED_FEATURES)}')
    print(f'Directions: {len(DUBNA_DIRECTION_KEYS)}')
    return df, multi_labels


def build_model(input_dim: int, num_classes: int):
    inputs = keras.Input(shape=(input_dim,))
    x = layers.Dense(256, activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(64, activation='relu')(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation='sigmoid')(x)
    model = keras.Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.Adam(0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', keras.metrics.AUC(name='auc')],
    )
    return model


def print_metrics(y_true, y_pred_proba, class_names):
    print('\n' + '=' * 80)
    print('КАЧЕСТВО МОДЕЛИ')
    print('=' * 80)

    y_pred_binary = (y_pred_proba >= 0.5).astype(int)
    top1 = top3 = top5 = 0
    n = len(y_true)

    for i in range(n):
        true = set(np.where(y_true[i] == 1)[0])
        if not true:
            continue
        pred_idx = np.argsort(y_pred_proba[i])[::-1]
        if pred_idx[0] in true:
            top1 += 1
        if any(idx in true for idx in pred_idx[:3]):
            top3 += 1
        if any(idx in true for idx in pred_idx[:5]):
            top5 += 1

    print(f'   Top-1 Accuracy:  {top1 / n:.2%}')
    print(f'   Top-3 Accuracy:  {top3 / n:.2%}')
    print(f'   Top-5 Accuracy:  {top5 / n:.2%}')

    macro_precision = precision_score(y_true, y_pred_binary, average='macro', zero_division=0)
    macro_recall = recall_score(y_true, y_pred_binary, average='macro', zero_division=0)
    macro_f1 = f1_score(y_true, y_pred_binary, average='macro', zero_division=0)
    print(f'   Macro Precision: {macro_precision:.2%}')
    print(f'   Macro Recall:    {macro_recall:.2%}')
    print(f'   Macro F1 Score:  {macro_f1:.2%}')

    try:
        auc = roc_auc_score(y_true, y_pred_proba, average='macro')
        print(f'   Macro AUC:      {auc:.3f}')
    except ValueError:
        print('   Macro AUC:      N/A')

    per_class_f1 = f1_score(y_true, y_pred_binary, average=None, zero_division=0)
    print('\n--- МЕТРИКИ ПО НАПРАВЛЕНИЯМ (F1 Score) ---')
    for i, name in enumerate(class_names):
        score = per_class_f1[i] * 100
        if score > 0:
            print(f'   {name[:35]:35} {score:5.1f}%')


def main():
    print('=' * 80)
    print(f'CareerAI training — {len(DUBNA_DIRECTION_KEYS)} directions')
    print('=' * 80)

    model_path = Path(MODEL_DIR)
    model_path.mkdir(exist_ok=True)

    df, multi_labels = generate_training_data()
    feature_cols = [c for c in df.columns if c != 'chosen_fields']
    X = df[feature_cols].values.astype('float32')

    mlb = MultiLabelBinarizer(classes=DUBNA_DIRECTION_KEYS)
    y = mlb.fit_transform(multi_labels)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42,
    )
    print(f'Train: {X_train.shape[0]}, Test: {X_test.shape[0]}')

    model = build_model(X.shape[1], len(DUBNA_DIRECTION_KEYS))
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor='val_auc', patience=15, mode='max', restore_best_weights=True,
        ),
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=8),
    ]
    model.fit(
        X_train, y_train,
        validation_split=0.2,
        epochs=80,
        batch_size=32,
        callbacks=callbacks,
        verbose=1,
    )

    y_pred_proba = model.predict(X_test, verbose=0)
    print_metrics(y_test, y_pred_proba, DUBNA_DIRECTION_KEYS)

    model.save(model_path / 'career_model.keras')
    joblib.dump(scaler, model_path / 'scaler.pkl')
    joblib.dump(mlb, model_path / 'multilabel_binarizer.pkl')

    with open(model_path / 'direction_key_skills.json', 'w', encoding='utf-8') as f:
        json.dump(DIRECTION_KEY_SKILLS, f, indent=2, ensure_ascii=False)

    print('\n' + '=' * 80)
    print('Модель сохранена в', model_path)
    print('=' * 80)


if __name__ == '__main__':
    main()
