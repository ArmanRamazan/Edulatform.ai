from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


BADGE_DEFINITIONS: dict[str, str] = {
    "first_enrollment": "Enroll in your first course",
    "streak_7": "Maintain a 7-day streak",
    "quiz_ace": "Score 100% on a quiz",
    "mastery_100": "Achieve full mastery on all course concepts",
}


@dataclass(frozen=True)
class Badge:
    id: UUID
    user_id: UUID
    badge_type: str
    unlocked_at: datetime


class BadgeResponse(BaseModel):
    badge_type: str
    description: str
    unlocked_at: datetime


class BadgeListResponse(BaseModel):
    badges: list[BadgeResponse]
    total: int
