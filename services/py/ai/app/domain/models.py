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


class LessonOutline(BaseModel):
    title: str
    description: str
    key_concepts: list[str]
    estimated_duration_minutes: int


class ModuleOutline(BaseModel):
    title: str
    description: str
    lessons: list[LessonOutline]


class CourseOutlineRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    level: str = Field(pattern=r"^(beginner|intermediate|advanced)$")
    target_audience: str = Field(min_length=1, max_length=500)
    num_modules: int = Field(default=5, ge=2, le=10)


class CourseOutlineResponse(BaseModel):
    modules: list[ModuleOutline]
    total_lessons: int
    estimated_duration_hours: int
    model_used: str


class LessonContentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    course_context: str | None = Field(default=None, max_length=500)
    format: str = Field(default="article", pattern=r"^(article|tutorial)$")


class LessonContentResponse(BaseModel):
    content: str
    key_concepts: list[str]
    estimated_duration_minutes: int
    model_used: str


class StudyPlanRequest(BaseModel):
    course_id: UUID
    available_hours_per_week: int = Field(default=10, ge=1, le=40)
    goal: str | None = Field(default=None, max_length=500)


class WeekPlan(BaseModel):
    week_number: int
    focus_areas: list[str]
    lessons_to_complete: list[str]
    flashcard_sessions: int
    quiz_practice: bool
    estimated_hours: float


class StudyPlanResponse(BaseModel):
    weeks: list[WeekPlan]
    estimated_completion: str
    total_estimated_hours: int
    model_used: str


class CoachStartRequest(BaseModel):
    mission_id: UUID
    personality: str = Field(default="friendly", max_length=50)


class CoachStartResponse(BaseModel):
    session_id: str
    content: str
    phase: str
    phase_progress: int


class CoachChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=2000)


class CoachChatResponse(BaseModel):
    session_id: str
    content: str
    phase: str
    phase_progress: int


class CoachEndRequest(BaseModel):
    session_id: str


class CoachEndResponse(BaseModel):
    session_id: str
    score: float
    mastery_delta: float
    duration_seconds: int
    strengths: list[str]
    gaps: list[str]


class MissionCompleteRequest(BaseModel):
    session_id: str
    concept_id: UUID
    org_id: UUID


class DailyMissionResponse(BaseModel):
    concept_name: str
    concept_id: UUID
    recap_questions: list[dict]
    reading_content: str
    check_questions: list[dict]
    code_case: dict | None


class MissionCompleteResponse(BaseModel):
    next_concept_preview: str | None
    total_completed: int
    score: float
    mastery_delta: float


class MasteryItem(BaseModel):
    concept_id: UUID
    mastery: float


class MissionDailyRequest(BaseModel):
    org_id: UUID
    mastery: list[MasteryItem] = []


class UnifiedSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    org_id: UUID
    org_terms: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


class InternalSearchResultResponse(BaseModel):
    title: str
    source_path: str
    content: str


class ExternalSearchResultResponse(BaseModel):
    title: str
    url: str
    snippet: str


class UnifiedSearchResponse(BaseModel):
    route: str
    internal_results: list[InternalSearchResultResponse]
    external_results: list[ExternalSearchResultResponse]


class ModerationRequest(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    content_type: str = Field(pattern=r"^(course_description|lesson_content|review_text)$")


class ModerationResponse(BaseModel):
    approved: bool
    flags: list[str]
    quality_score: int
    suggestions: list[str]
