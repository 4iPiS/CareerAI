"""Схемы публичного API v1."""

from typing import Any, Optional

from pydantic import BaseModel


class QuestionPayload(BaseModel):
    id: str
    text: str
    image_url: Optional[str] = None
    type: str = 'rating_1_5'
    options: Optional[dict] = None
    context: Optional[str] = None
    progress: Optional[dict] = None
    is_salary: bool = False
    is_custom: bool = False
    is_ege: bool = False
    is_ege_select: bool = False
    subjects: Optional[list] = None
    fields: Optional[list] = None
    consent_text: Optional[str] = None


class StartResponse(BaseModel):
    session_id: str
    question: QuestionPayload


class AnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: Any


class AnswerResponse(BaseModel):
    done: bool
    session_id: str
    question: Optional[QuestionPayload] = None
    recommendations: Optional[list] = None
    stats: Optional[dict] = None


class SurveyDataRequest(BaseModel):
    session_id: str
    data: dict = {}
    consent: bool = False


class FeedbackRequest(BaseModel):
    session_id: str
    chosen_fields: list = []
    feedback_score: Optional[int] = None