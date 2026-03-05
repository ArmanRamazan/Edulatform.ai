from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Mission:
    id: UUID
    user_id: UUID
    organization_id: UUID
    concept_id: UUID | None
    mission_type: str
    status: str
    blueprint: dict
    score: float | None
    mastery_delta: float | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
