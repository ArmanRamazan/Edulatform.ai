from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.badge import BADGE_DEFINITIONS, Badge
from app.repositories.badge_repo import BadgeRepository
from app.services.badge_service import BadgeService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_badge_repo():
    return AsyncMock(spec=BadgeRepository)


@pytest.fixture
def badge_service(mock_badge_repo):
    return BadgeService(repo=mock_badge_repo)


def _make_badge(user_id, badge_type: str = "streak_7") -> Badge:
    return Badge(
        id=uuid4(),
        user_id=user_id,
        badge_type=badge_type,
        unlocked_at=datetime.now(timezone.utc),
    )


class TestTryUnlock:
    async def test_unlocks_new_badge(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "streak_7")
        mock_badge_repo.create.return_value = badge

        result = await badge_service.try_unlock(user_id, "streak_7")

        assert result.badge_type == "streak_7"
        assert result.user_id == user_id
        mock_badge_repo.create.assert_awaited_once_with(user_id, "streak_7")

    async def test_idempotent_returns_existing(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "quiz_ace")
        mock_badge_repo.create.return_value = badge

        result1 = await badge_service.try_unlock(user_id, "quiz_ace")
        result2 = await badge_service.try_unlock(user_id, "quiz_ace")

        assert result1.badge_type == result2.badge_type

    async def test_unknown_badge_type_raises(
        self, badge_service, user_id
    ):
        with pytest.raises(ValueError, match="Unknown badge type"):
            await badge_service.try_unlock(user_id, "nonexistent_badge")

    async def test_all_valid_badge_types(
        self, badge_service, mock_badge_repo, user_id
    ):
        for badge_type in BADGE_DEFINITIONS:
            badge = _make_badge(user_id, badge_type)
            mock_badge_repo.create.return_value = badge

            result = await badge_service.try_unlock(user_id, badge_type)
            assert result.badge_type == badge_type


class TestGetBadges:
    async def test_returns_all_badges(
        self, badge_service, mock_badge_repo, user_id
    ):
        badges = [
            _make_badge(user_id, "streak_7"),
            _make_badge(user_id, "quiz_ace"),
        ]
        mock_badge_repo.get_all.return_value = badges

        result = await badge_service.get_badges(user_id)

        assert result.total == 2
        assert len(result.badges) == 2
        assert result.badges[0].badge_type == "streak_7"
        assert result.badges[0].description == BADGE_DEFINITIONS["streak_7"]
        assert result.badges[1].badge_type == "quiz_ace"

    async def test_empty_returns_zero(
        self, badge_service, mock_badge_repo, user_id
    ):
        mock_badge_repo.get_all.return_value = []

        result = await badge_service.get_badges(user_id)

        assert result.total == 0
        assert result.badges == []


class TestCheckStreakBadge:
    async def test_unlocks_at_7_days(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "streak_7")
        mock_badge_repo.create.return_value = badge

        result = await badge_service.check_streak_badge(user_id, 7)

        assert result is not None
        assert result.badge_type == "streak_7"

    async def test_unlocks_above_7_days(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "streak_7")
        mock_badge_repo.create.return_value = badge

        result = await badge_service.check_streak_badge(user_id, 15)

        assert result is not None
        assert result.badge_type == "streak_7"

    async def test_no_unlock_at_6_days(
        self, badge_service, mock_badge_repo, user_id
    ):
        result = await badge_service.check_streak_badge(user_id, 6)

        assert result is None
        mock_badge_repo.create.assert_not_awaited()

    async def test_no_unlock_at_zero(
        self, badge_service, mock_badge_repo, user_id
    ):
        result = await badge_service.check_streak_badge(user_id, 0)

        assert result is None
        mock_badge_repo.create.assert_not_awaited()


class TestCheckQuizAceBadge:
    async def test_unlocks_at_perfect_score(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "quiz_ace")
        mock_badge_repo.create.return_value = badge

        result = await badge_service.check_quiz_ace_badge(user_id, 1.0)

        assert result is not None
        assert result.badge_type == "quiz_ace"

    async def test_no_unlock_at_99_percent(
        self, badge_service, mock_badge_repo, user_id
    ):
        result = await badge_service.check_quiz_ace_badge(user_id, 0.99)

        assert result is None
        mock_badge_repo.create.assert_not_awaited()

    async def test_no_unlock_at_zero(
        self, badge_service, mock_badge_repo, user_id
    ):
        result = await badge_service.check_quiz_ace_badge(user_id, 0.0)

        assert result is None


class TestCheckMasteryBadge:
    async def test_unlocks_at_full_mastery(
        self, badge_service, mock_badge_repo, user_id
    ):
        badge = _make_badge(user_id, "mastery_100")
        mock_badge_repo.create.return_value = badge

        result = await badge_service.check_mastery_badge(user_id, 1.0)

        assert result is not None
        assert result.badge_type == "mastery_100"

    async def test_no_unlock_below_full_mastery(
        self, badge_service, mock_badge_repo, user_id
    ):
        result = await badge_service.check_mastery_badge(user_id, 0.95)

        assert result is None
        mock_badge_repo.create.assert_not_awaited()
