from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.leaderboard import LeaderboardEntry
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.services.leaderboard_service import LeaderboardService

from common.errors import NotFoundError


@pytest.fixture
def student_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_leaderboard_repo():
    return AsyncMock(spec=LeaderboardRepository)


@pytest.fixture
def leaderboard_service(mock_leaderboard_repo):
    return LeaderboardService(repo=mock_leaderboard_repo)


def _make_entry(
    student_id=None,
    course_id=None,
    score: int = 0,
    opted_in: bool = True,
) -> LeaderboardEntry:
    return LeaderboardEntry(
        id=uuid4(),
        student_id=student_id or uuid4(),
        course_id=course_id or uuid4(),
        score=score,
        opted_in=opted_in,
        updated_at=datetime.now(timezone.utc),
    )


class TestOptIn:
    async def test_opt_in_creates_entry(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(student_id=student_id, course_id=course_id)
        mock_leaderboard_repo.opt_in.return_value = entry

        result = await leaderboard_service.opt_in(student_id, course_id)

        assert result.opted_in is True
        assert result.course_id == course_id
        mock_leaderboard_repo.opt_in.assert_awaited_once_with(student_id, course_id)

    async def test_opt_in_idempotent_preserves_score(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(student_id=student_id, course_id=course_id, score=150)
        mock_leaderboard_repo.opt_in.return_value = entry

        result = await leaderboard_service.opt_in(student_id, course_id)

        assert result.score == 150
        assert result.opted_in is True


class TestOptOut:
    async def test_opt_out_sets_opted_in_false(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(
            student_id=student_id, course_id=course_id, score=100, opted_in=False
        )
        mock_leaderboard_repo.opt_out.return_value = entry

        result = await leaderboard_service.opt_out(student_id, course_id)

        assert result.opted_in is False
        assert result.score == 100
        mock_leaderboard_repo.opt_out.assert_awaited_once_with(student_id, course_id)

    async def test_opt_out_not_found_raises(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        mock_leaderboard_repo.opt_out.return_value = None

        with pytest.raises(NotFoundError):
            await leaderboard_service.opt_out(student_id, course_id)


class TestAddScore:
    async def test_add_score_increments_points(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(student_id=student_id, course_id=course_id, score=30)
        mock_leaderboard_repo.add_score.return_value = entry

        result = await leaderboard_service.add_score(student_id, course_id, 20)

        assert result.score == 30
        mock_leaderboard_repo.add_score.assert_awaited_once_with(
            student_id, course_id, 20
        )

    async def test_add_score_not_opted_in_raises(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        mock_leaderboard_repo.add_score.return_value = None

        with pytest.raises(NotFoundError):
            await leaderboard_service.add_score(student_id, course_id, 10)


class TestGetLeaderboard:
    async def test_get_leaderboard_returns_ranked_entries(
        self, leaderboard_service, mock_leaderboard_repo, course_id
    ):
        entries = [
            _make_entry(course_id=course_id, score=200),
            _make_entry(course_id=course_id, score=150),
            _make_entry(course_id=course_id, score=100),
        ]
        mock_leaderboard_repo.get_leaderboard.return_value = (entries, 3)

        result = await leaderboard_service.get_leaderboard(course_id, limit=10, offset=0)

        assert result.course_id == course_id
        assert result.total == 3
        assert len(result.entries) == 3
        assert result.entries[0].rank == 1
        assert result.entries[0].score == 200
        assert result.entries[1].rank == 2
        assert result.entries[2].rank == 3

    async def test_get_leaderboard_with_offset(
        self, leaderboard_service, mock_leaderboard_repo, course_id
    ):
        entries = [
            _make_entry(course_id=course_id, score=50),
        ]
        mock_leaderboard_repo.get_leaderboard.return_value = (entries, 5)

        result = await leaderboard_service.get_leaderboard(course_id, limit=1, offset=4)

        assert result.total == 5
        assert len(result.entries) == 1
        assert result.entries[0].rank == 5

    async def test_get_leaderboard_empty(
        self, leaderboard_service, mock_leaderboard_repo, course_id
    ):
        mock_leaderboard_repo.get_leaderboard.return_value = ([], 0)

        result = await leaderboard_service.get_leaderboard(course_id, limit=10, offset=0)

        assert result.total == 0
        assert result.entries == []


class TestGetMyRank:
    async def test_get_my_rank_returns_position(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(student_id=student_id, course_id=course_id, score=100)
        mock_leaderboard_repo.get_entry.return_value = entry
        mock_leaderboard_repo.get_rank.return_value = 3

        result = await leaderboard_service.get_my_rank(student_id, course_id)

        assert result.rank == 3
        assert result.score == 100
        assert result.opted_in is True
        assert result.course_id == course_id

    async def test_get_my_rank_not_found_raises(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        mock_leaderboard_repo.get_entry.return_value = None

        with pytest.raises(NotFoundError):
            await leaderboard_service.get_my_rank(student_id, course_id)

    async def test_get_my_rank_opted_out_still_returns(
        self, leaderboard_service, mock_leaderboard_repo, student_id, course_id
    ):
        entry = _make_entry(
            student_id=student_id, course_id=course_id, score=50, opted_in=False
        )
        mock_leaderboard_repo.get_entry.return_value = entry
        mock_leaderboard_repo.get_rank.return_value = None

        result = await leaderboard_service.get_my_rank(student_id, course_id)

        assert result.opted_in is False
        assert result.rank == 0
        assert result.score == 50
