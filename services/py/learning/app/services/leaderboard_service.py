from __future__ import annotations

from uuid import UUID

from common.errors import NotFoundError
from app.domain.leaderboard import (
    LeaderboardEntryResponse,
    LeaderboardResponse,
    MyRankResponse,
    OptInResponse,
)
from app.repositories.leaderboard_repo import LeaderboardRepository


class LeaderboardService:
    def __init__(self, repo: LeaderboardRepository) -> None:
        self._repo = repo

    async def opt_in(self, student_id: UUID, course_id: UUID) -> OptInResponse:
        entry = await self._repo.opt_in(student_id, course_id)
        return OptInResponse(
            course_id=entry.course_id,
            opted_in=entry.opted_in,
            score=entry.score,
        )

    async def opt_out(self, student_id: UUID, course_id: UUID) -> OptInResponse:
        entry = await self._repo.opt_out(student_id, course_id)
        if entry is None:
            raise NotFoundError("Leaderboard entry not found")
        return OptInResponse(
            course_id=entry.course_id,
            opted_in=entry.opted_in,
            score=entry.score,
        )

    async def add_score(
        self, student_id: UUID, course_id: UUID, points: int,
    ) -> OptInResponse:
        entry = await self._repo.add_score(student_id, course_id, points)
        if entry is None:
            raise NotFoundError("Leaderboard entry not found")
        return OptInResponse(
            course_id=entry.course_id,
            opted_in=entry.opted_in,
            score=entry.score,
        )

    async def get_leaderboard(
        self, course_id: UUID, limit: int = 20, offset: int = 0,
    ) -> LeaderboardResponse:
        entries, total = await self._repo.get_leaderboard(course_id, limit, offset)
        return LeaderboardResponse(
            course_id=course_id,
            entries=[
                LeaderboardEntryResponse(
                    student_id=e.student_id,
                    score=e.score,
                    rank=offset + i + 1,
                )
                for i, e in enumerate(entries)
            ],
            total=total,
        )

    async def get_my_rank(self, student_id: UUID, course_id: UUID) -> MyRankResponse:
        entry = await self._repo.get_entry(student_id, course_id)
        if entry is None:
            raise NotFoundError("Leaderboard entry not found")

        rank = 0
        if entry.opted_in:
            rank = await self._repo.get_rank(student_id, course_id) or 0

        return MyRankResponse(
            course_id=course_id,
            score=entry.score,
            rank=rank,
            opted_in=entry.opted_in,
        )
