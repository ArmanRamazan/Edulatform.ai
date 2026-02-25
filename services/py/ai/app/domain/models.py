from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ModelTier(StrEnum):
    CHEAP = "cheap"
    MID = "mid"
    EXPENSIVE = "expensive"


MODEL_TIER_MAP: dict[str, ModelTier] = {
    "quiz": ModelTier.CHEAP,
    "summary": ModelTier.CHEAP,
    "tutor": ModelTier.CHEAP,
}


class QuestionData(BaseModel):
    text: str
    options: list[str] = Field(min_length=2, max_length=6)
    correct_index: int
    explanation: str


class QuizRequest(BaseModel):
    lesson_id: UUID
    content: str = Field(min_length=10, max_length=50000)


class QuizResponse(BaseModel):
    lesson_id: UUID
    questions: list[QuestionData]
    model_used: str
    cached: bool


class SummaryRequest(BaseModel):
    lesson_id: UUID
    content: str = Field(min_length=10, max_length=50000)


class SummaryResponse(BaseModel):
    lesson_id: UUID
    summary: str
    model_used: str
    cached: bool


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class TutorChatRequest(BaseModel):
    lesson_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    lesson_content: str = Field(min_length=10, max_length=50000)
    session_id: str | None = None


class TutorChatResponse(BaseModel):
    session_id: str
    message: str
    model_used: str
    credits_remaining: int


class TutorFeedbackRequest(BaseModel):
    session_id: str
    message_index: int = Field(ge=0)
    rating: int = Field(ge=-1, le=1)


class TutorFeedbackResponse(BaseModel):
    status: str
