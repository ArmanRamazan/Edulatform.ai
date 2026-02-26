from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.xp import XP_REWARDS, XpEvent
from app.repositories.xp_repo import XpRepository
from app.services.xp_service import XpService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_xp_repo():
    return AsyncMock(spec=XpRepository)


@pytest.fixture
def xp_service(mock_xp_repo):
    return XpService(repo=mock_xp_repo)


def _make_xp_event(
    user_id,
    action: str = "lesson_complete",
    points: int = 10,
    course_id=None,
) -> XpEvent:
    return XpEvent(
        id=uuid4(),
        user_id=user_id,
        action=action,
        points=points,
        course_id=course_id,
        created_at=datetime.now(timezone.utc),
    )


class TestAward:
    async def test_lesson_complete_gives_10_xp(
        self, xp_service, mock_xp_repo, user_id, course_id
    ):
        event = _make_xp_event(user_id, "lesson_complete", 10, course_id)
        mock_xp_repo.create_event.return_value = event

        result = await xp_service.award(user_id, "lesson_complete", course_id)

        assert result.points == 10
        assert result.action == "lesson_complete"
        mock_xp_repo.create_event.assert_awaited_once_with(
            user_id, "lesson_complete", 10, course_id,
        )

    async def test_quiz_submit_gives_20_xp(
        self, xp_service, mock_xp_repo, user_id
    ):
        event = _make_xp_event(user_id, "quiz_submit", 20)
        mock_xp_repo.create_event.return_value = event

        result = await xp_service.award(user_id, "quiz_submit")

        assert result.points == 20
        assert result.action == "quiz_submit"
        mock_xp_repo.create_event.assert_awaited_once_with(
            user_id, "quiz_submit", 20, None,
        )

    async def test_flashcard_review_gives_5_xp(
        self, xp_service, mock_xp_repo, user_id
    ):
        event = _make_xp_event(user_id, "flashcard_review", 5)
        mock_xp_repo.create_event.return_value = event

        result = await xp_service.award(user_id, "flashcard_review")

        assert result.points == 5
        assert result.action == "flashcard_review"

    async def test_unknown_action_raises_value_error(
        self, xp_service, user_id
    ):
        with pytest.raises(ValueError, match="Unknown XP action"):
            await xp_service.award(user_id, "invalid_action")

    async def test_award_without_course_id(
        self, xp_service, mock_xp_repo, user_id
    ):
        event = _make_xp_event(user_id, "lesson_complete", 10)
        mock_xp_repo.create_event.return_value = event

        result = await xp_service.award(user_id, "lesson_complete")

        assert result.course_id is None

    async def test_xp_rewards_map_correct_values(self):
        assert XP_REWARDS["lesson_complete"] == 10
        assert XP_REWARDS["quiz_submit"] == 20
        assert XP_REWARDS["flashcard_review"] == 5
        assert len(XP_REWARDS) == 3


class TestGetTotal:
    async def test_returns_sum_of_all_events(
        self, xp_service, mock_xp_repo, user_id
    ):
        mock_xp_repo.get_total.return_value = 75

        result = await xp_service.get_total(user_id)

        assert result == 75
        mock_xp_repo.get_total.assert_awaited_once_with(user_id)

    async def test_no_events_returns_zero(
        self, xp_service, mock_xp_repo, user_id
    ):
        mock_xp_repo.get_total.return_value = 0

        result = await xp_service.get_total(user_id)

        assert result == 0


class TestGetSummary:
    async def test_returns_total_and_events(
        self, xp_service, mock_xp_repo, user_id, course_id
    ):
        events = [
            _make_xp_event(user_id, "lesson_complete", 10, course_id),
            _make_xp_event(user_id, "quiz_submit", 20, course_id),
        ]
        mock_xp_repo.get_total.return_value = 30
        mock_xp_repo.get_history.return_value = events

        result = await xp_service.get_summary(user_id)

        assert result.total_xp == 30
        assert len(result.events) == 2
        assert result.events[0].action == "lesson_complete"
        assert result.events[0].points == 10
        assert result.events[1].action == "quiz_submit"
        assert result.events[1].points == 20

    async def test_empty_history(
        self, xp_service, mock_xp_repo, user_id
    ):
        mock_xp_repo.get_total.return_value = 0
        mock_xp_repo.get_history.return_value = []

        result = await xp_service.get_summary(user_id)

        assert result.total_xp == 0
        assert result.events == []

    async def test_passes_pagination_params(
        self, xp_service, mock_xp_repo, user_id
    ):
        mock_xp_repo.get_total.return_value = 0
        mock_xp_repo.get_history.return_value = []

        await xp_service.get_summary(user_id, limit=5, offset=10)

        mock_xp_repo.get_history.assert_awaited_once_with(user_id, 5, 10)
