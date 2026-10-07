"""Схемы админ-API."""

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    password: Optional[str] = None
    current_password: Optional[str] = None
    is_active: Optional[bool] = None


class UserDelete(BaseModel):
    password: str


class DirectionPayload(BaseModel):
    name: str
    fgos_code: str = ''
    description: str = ''
    key_skills_text: str = ''
    category: str = ''
    avg_salary: int = 0
    employment_rate: int = 0
    study_years: int = 4
    ege_typical: str = ''
    image_path: str = ''
    sort_order: int = 0
    is_active: bool = True
    skill_codes: list[str] = []


class FeaturePayload(BaseModel):
    code: str
    label: str
    data_type: str = 'rating_1_5'
    default_value: str = '3.0'
    is_common: bool = False
    sort_order: int = 0
    is_active: bool = True


class QuestionPayload(BaseModel):
    group_code: str
    feature_code: Optional[str] = None
    text: str
    image_url: Optional[str] = None
    question_type: str = 'rating_1_5'
    options: Optional[dict] = None
    threshold: Optional[float] = None
    level: int = 0
    activation_condition: Optional[dict] = None
    sort_order: int = 0
    is_active: bool = True


class CustomFieldPayload(BaseModel):
    code: str
    label: str
    field_type: str = 'text'
    options: Optional[list[str]] = None
    required: bool = False
    sort_order: int = 0
    is_active: bool = True


class SettingsPayload(BaseModel):
    university_name: Optional[str] = None
    university_url: Optional[str] = None
    abitur_url: Optional[str] = None
    tagline: Optional[str] = None
    logo_path: Optional[str] = None
    hero_image_path: Optional[str] = None
    presenter_video_path: Optional[str] = None
    primary_color: Optional[str] = None
    primary_alpha: Optional[float] = None
    consent_text: Optional[str] = None
    custom_form_position: Optional[str] = None