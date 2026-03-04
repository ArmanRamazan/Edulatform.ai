from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PathConcept:
    concept_id: UUID
    name: str
    priority: int  # 1=critical, 2=important, 3=nice-to-have
    estimated_sessions: int
    prerequisites: list[UUID]
    mastery: float  # current mastery 0-1


@dataclass(frozen=True)
class LearningPath:
    user_id: UUID
    organization_id: UUID
    concepts_ordered: list[PathConcept]
    current_index: int
    created_at: datetime
