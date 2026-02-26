from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Streak:
    user_id: UUID
    current_streak: int
    longest_streak: int
    last_activity_date: date
    updated_at: datetime


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_activity_date: date | None
    active_today: bool


class AtRiskResponse(BaseModel):
    user_ids: list[UUID]
