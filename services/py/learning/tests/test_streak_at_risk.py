from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.streak import Streak
from app.repositories.streak_repo import StreakRepository
from app.services.streak_service import StreakService


@pytest.fixture
def mock_streak_repo():
    return AsyncMock(spec=StreakRepository)


@pytest.fixture
def streak_service(mock_streak_repo):
    return StreakService(repo=mock_streak_repo)


class TestGetAtRiskUserIds:
    async def test_returns_users_with_yesterday_activity(
        self, streak_service, mock_streak_repo
    ):
        user1, user2 = uuid4(), uuid4()
        mock_streak_repo.get_at_risk_user_ids.return_value = [user1, user2]

        result = await streak_service.get_at_risk_user_ids()

        assert result == [user1, user2]
        mock_streak_repo.get_at_risk_user_ids.assert_awaited_once()

    async def test_returns_empty_when_no_at_risk(
        self, streak_service, mock_streak_repo
    ):
        mock_streak_repo.get_at_risk_user_ids.return_value = []

        result = await streak_service.get_at_risk_user_ids()

        assert result == []
