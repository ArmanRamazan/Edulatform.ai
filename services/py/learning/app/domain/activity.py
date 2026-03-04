from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ActivityType(StrEnum):
    quiz_completed = "quiz_completed"
    flashcard_reviewed = "flashcard_reviewed"
    badge_earned = "badge_earned"
    streak_milestone = "streak_milestone"
    concept_mastered = "concept_mastered"


@dataclass(frozen=True)
class Activity:
    id: UUID
    user_id: UUID
    activity_type: str
    payload: dict
    created_at: datetime


class ActivityResponse(BaseModel):
    id: UUID
    user_id: UUID
    activity_type: str
    payload: dict
    created_at: datetime


class ActivityListResponse(BaseModel):
    activities: list[ActivityResponse]
    total: int
