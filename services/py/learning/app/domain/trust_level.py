from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


LEVEL_THRESHOLDS: dict[int, dict[str, int]] = {
    1: {"missions": 5, "concepts_mastered": 3},
    2: {"missions": 15, "concepts_mastered": 8},
    3: {"missions": 30, "concepts_mastered": 15},
    4: {"missions": 50, "concepts_mastered": 25},
    5: {"missions": 80, "concepts_mastered": 40},
}

LEVEL_NAMES: dict[int, str] = {
    0: "Newcomer",
    1: "Explorer",
    2: "Contributor",
    3: "Builder",
    4: "Guardian",
    5: "Architect",
}


@dataclass(frozen=True)
class TrustLevel:
    id: UUID
    user_id: UUID
    organization_id: UUID
    level: int
    total_missions_completed: int
    total_concepts_mastered: int
    unlocked_areas: list[str]
    level_up_at: datetime | None
    created_at: datetime


class NextLevelProgress(BaseModel):
    level: int
    level_name: str
    missions_required: int
    concepts_required: int
    missions_remaining: int
    concepts_remaining: int


class TrustLevelResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    level: int
    level_name: str
    total_missions_completed: int
    total_concepts_mastered: int
    unlocked_areas: list[str]
    level_up_at: datetime | None
    next_level: NextLevelProgress | None


class TrustLevelListResponse(BaseModel):
    levels: list[TrustLevelResponse]
