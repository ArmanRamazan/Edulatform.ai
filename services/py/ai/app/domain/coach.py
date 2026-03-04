from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoachMessage:
    content: str
    phase: str
    phase_progress: int
    session_id: str


@dataclass(frozen=True)
class SessionResult:
    session_id: str
    score: float
    mastery_delta: float
    duration_seconds: int
    strengths: list[str]
    gaps: list[str]
