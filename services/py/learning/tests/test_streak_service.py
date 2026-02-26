from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.streak import Streak
from app.repositories.streak_repo import StreakRepository
from app.services.streak_service import StreakService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_streak_repo():
    return AsyncMock(spec=StreakRepository)


@pytest.fixture
def streak_service(mock_streak_repo):
    return StreakService(repo=mock_streak_repo)


def _make_streak(
    user_id,
    current: int = 1,
    longest: int = 1,
    last_date: date | None = None,
) -> Streak:
    return Streak(
        user_id=user_id,
        current_streak=current,
        longest_streak=longest,
        last_activity_date=last_date or date.today(),
        updated_at=datetime.now(timezone.utc),
    )


class TestRecordActivity:
    async def test_first_activity_creates_streak(
        self, streak_service, mock_streak_repo, user_id
    ):
        mock_streak_repo.get_by_user.return_value = None
        mock_streak_repo.upsert.return_value = _make_streak(user_id)

        result = await streak_service.record_activity(user_id)

        assert result.current_streak == 1
        assert result.longest_streak == 1
        mock_streak_repo.upsert.assert_awaited_once_with(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
        )

    async def test_same_day_activity_is_noop(
        self, streak_service, mock_streak_repo, user_id
    ):
        existing = _make_streak(user_id, current=3, longest=5)
        mock_streak_repo.get_by_user.return_value = existing

        result = await streak_service.record_activity(user_id)

        assert result.current_streak == 3
        assert result.longest_streak == 5
        mock_streak_repo.upsert.assert_not_awaited()

    async def test_next_day_increments_streak(
        self, streak_service, mock_streak_repo, user_id
    ):
        yesterday = date.today() - timedelta(days=1)
        existing = _make_streak(user_id, current=3, longest=5, last_date=yesterday)
        mock_streak_repo.get_by_user.return_value = existing
        mock_streak_repo.upsert.return_value = _make_streak(
            user_id, current=4, longest=5
        )

        result = await streak_service.record_activity(user_id)

        assert result.current_streak == 4
        mock_streak_repo.upsert.assert_awaited_once_with(
            user_id=user_id,
            current_streak=4,
            longest_streak=5,
        )

    async def test_next_day_updates_longest_when_exceeded(
        self, streak_service, mock_streak_repo, user_id
    ):
        yesterday = date.today() - timedelta(days=1)
        existing = _make_streak(user_id, current=5, longest=5, last_date=yesterday)
        mock_streak_repo.get_by_user.return_value = existing
        mock_streak_repo.upsert.return_value = _make_streak(
            user_id, current=6, longest=6
        )

        result = await streak_service.record_activity(user_id)

        assert result.current_streak == 6
        assert result.longest_streak == 6
        mock_streak_repo.upsert.assert_awaited_once_with(
            user_id=user_id,
            current_streak=6,
            longest_streak=6,
        )

    async def test_gap_resets_streak_to_one(
        self, streak_service, mock_streak_repo, user_id
    ):
        three_days_ago = date.today() - timedelta(days=3)
        existing = _make_streak(
            user_id, current=10, longest=10, last_date=three_days_ago
        )
        mock_streak_repo.get_by_user.return_value = existing
        mock_streak_repo.upsert.return_value = _make_streak(
            user_id, current=1, longest=10
        )

        result = await streak_service.record_activity(user_id)

        assert result.current_streak == 1
        assert result.longest_streak == 10
        mock_streak_repo.upsert.assert_awaited_once_with(
            user_id=user_id,
            current_streak=1,
            longest_streak=10,
        )


class TestGetStreak:
    async def test_no_streak_returns_defaults(
        self, streak_service, mock_streak_repo, user_id
    ):
        mock_streak_repo.get_by_user.return_value = None

        result = await streak_service.get_streak(user_id)

        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.last_activity_date is None
        assert result.active_today is False

    async def test_active_today(
        self, streak_service, mock_streak_repo, user_id
    ):
        existing = _make_streak(user_id, current=3, longest=5)
        mock_streak_repo.get_by_user.return_value = existing

        result = await streak_service.get_streak(user_id)

        assert result.current_streak == 3
        assert result.longest_streak == 5
        assert result.active_today is True

    async def test_yesterday_streak_still_alive(
        self, streak_service, mock_streak_repo, user_id
    ):
        yesterday = date.today() - timedelta(days=1)
        existing = _make_streak(user_id, current=7, longest=7, last_date=yesterday)
        mock_streak_repo.get_by_user.return_value = existing

        result = await streak_service.get_streak(user_id)

        assert result.current_streak == 7
        assert result.active_today is False

    async def test_broken_streak_shows_zero(
        self, streak_service, mock_streak_repo, user_id
    ):
        old_date = date.today() - timedelta(days=3)
        existing = _make_streak(user_id, current=10, longest=10, last_date=old_date)
        mock_streak_repo.get_by_user.return_value = existing

        result = await streak_service.get_streak(user_id)

        assert result.current_streak == 0
        assert result.longest_streak == 10
        assert result.active_today is False
