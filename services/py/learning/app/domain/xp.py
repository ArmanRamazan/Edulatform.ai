from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


XP_REWARDS: dict[str, int] = {
    "lesson_complete": 10,
    "quiz_submit": 20,
    "flashcard_review": 5,
}


@dataclass(frozen=True)
class XpEvent:
    id: UUID
    user_id: UUID
    action: str
    points: int
    course_id: UUID | None
    created_at: datetime


class XpEventResponse(BaseModel):
    action: str
    points: int
    course_id: UUID | None
    created_at: datetime


class XpSummaryResponse(BaseModel):
    total_xp: int
    events: list[XpEventResponse]
