from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class LeaderboardEntry:
    id: UUID
    student_id: UUID
    course_id: UUID
    score: int
    opted_in: bool
    updated_at: datetime


class LeaderboardEntryResponse(BaseModel):
    student_id: UUID
    score: int
    rank: int


class LeaderboardResponse(BaseModel):
    course_id: UUID
    entries: list[LeaderboardEntryResponse]
    total: int


class MyRankResponse(BaseModel):
    course_id: UUID
    score: int
    rank: int
    opted_in: bool


class OptInResponse(BaseModel):
    course_id: UUID
    opted_in: bool
    score: int


class AddScoreRequest(BaseModel):
    points: int
