from __future__ import annotations

from dataclasses import dataclass

from app.domain.mission import Mission
from app.domain.trust_level import TrustLevel


@dataclass(frozen=True)
class DailySummary:
    mission: Mission | None
    trust_level: TrustLevel
    due_flashcards: int
    streak_days: int
    greeting: str
