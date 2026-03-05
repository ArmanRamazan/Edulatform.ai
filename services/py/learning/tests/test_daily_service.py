from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.daily import DailySummary
from app.domain.mission import Mission
from app.domain.streak import StreakResponse
from app.domain.trust_level import TrustLevel
from app.services.daily_service import DailyService
from app.services.mission_service import MissionService
from app.services.trust_level_service import TrustLevelService
from app.services.flashcard_service import FlashcardService
from app.services.streak_service import StreakService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_mission_service():
    return AsyncMock(spec=MissionService)


@pytest.fixture
def mock_trust_level_service():
    return AsyncMock(spec=TrustLevelService)


@pytest.fixture
def mock_flashcard_service():
    return AsyncMock(spec=FlashcardService)


@pytest.fixture
def mock_streak_service():
    return AsyncMock(spec=StreakService)


@pytest.fixture
def daily_service(
    mock_mission_service,
    mock_trust_level_service,
    mock_flashcard_service,
    mock_streak_service,
):
    return DailyService(
        mission_service=mock_mission_service,
        trust_level_service=mock_trust_level_service,
        flashcard_service=mock_flashcard_service,
        streak_service=mock_streak_service,
    )


def _make_mission(user_id, org_id, concept_name: str = "CI/CD") -> Mission:
    return Mission(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        concept_id=uuid4(),
        mission_type="daily",
        status="pending",
        blueprint={"concept_name": concept_name, "questions": []},
        score=None,
        mastery_delta=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


def _make_trust_level(user_id, org_id, level: int = 2) -> TrustLevel:
    return TrustLevel(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        level=level,
        total_missions_completed=15,
        total_concepts_mastered=8,
        unlocked_areas=["quizzes", "discussions"],
        level_up_at=None,
        created_at=datetime.now(timezone.utc),
    )


class TestGetDailySummary:
    async def test_aggregates_all_data(
        self,
        daily_service,
        mock_mission_service,
        mock_trust_level_service,
        mock_flashcard_service,
        mock_streak_service,
        user_id,
        org_id,
    ):
        mission = _make_mission(user_id, org_id, concept_name="CI/CD")
        trust_level = _make_trust_level(user_id, org_id)
        streak_resp = StreakResponse(
            current_streak=12,
            longest_streak=30,
            last_activity_date=None,
            active_today=True,
        )

        mock_mission_service.get_or_create_today.return_value = mission
        mock_trust_level_service.get_my_level.return_value = trust_level
        mock_flashcard_service.get_due_cards.return_value = ([], 5)
        mock_streak_service.get_streak.return_value = streak_resp

        result = await daily_service.get_daily_summary(
            user_id=user_id, org_id=org_id, token="tok",
        )

        assert isinstance(result, DailySummary)
        assert result.mission == mission
        assert result.trust_level == trust_level
        assert result.due_flashcards == 5
        assert result.streak_days == 12

    async def test_greeting_includes_streak_and_concept(
        self,
        daily_service,
        mock_mission_service,
        mock_trust_level_service,
        mock_flashcard_service,
        mock_streak_service,
        user_id,
        org_id,
    ):
        mission = _make_mission(user_id, org_id, concept_name="Docker")
        trust_level = _make_trust_level(user_id, org_id)
        streak_resp = StreakResponse(
            current_streak=7,
            longest_streak=10,
            last_activity_date=None,
            active_today=False,
        )

        mock_mission_service.get_or_create_today.return_value = mission
        mock_trust_level_service.get_my_level.return_value = trust_level
        mock_flashcard_service.get_due_cards.return_value = ([], 3)
        mock_streak_service.get_streak.return_value = streak_resp

        result = await daily_service.get_daily_summary(
            user_id=user_id, org_id=org_id, token="tok",
        )

        assert "7" in result.greeting
        assert "Docker" in result.greeting

    async def test_handles_no_mission(
        self,
        daily_service,
        mock_mission_service,
        mock_trust_level_service,
        mock_flashcard_service,
        mock_streak_service,
        user_id,
        org_id,
    ):
        trust_level = _make_trust_level(user_id, org_id)
        streak_resp = StreakResponse(
            current_streak=0,
            longest_streak=5,
            last_activity_date=None,
            active_today=False,
        )

        mock_mission_service.get_or_create_today.return_value = None
        mock_trust_level_service.get_my_level.return_value = trust_level
        mock_flashcard_service.get_due_cards.return_value = ([], 0)
        mock_streak_service.get_streak.return_value = streak_resp

        result = await daily_service.get_daily_summary(
            user_id=user_id, org_id=org_id, token="tok",
        )

        assert result.mission is None
        assert result.streak_days == 0

    async def test_handles_zero_streak(
        self,
        daily_service,
        mock_mission_service,
        mock_trust_level_service,
        mock_flashcard_service,
        mock_streak_service,
        user_id,
        org_id,
    ):
        mission = _make_mission(user_id, org_id, concept_name="Git")
        trust_level = _make_trust_level(user_id, org_id)
        streak_resp = StreakResponse(
            current_streak=0,
            longest_streak=0,
            last_activity_date=None,
            active_today=False,
        )

        mock_mission_service.get_or_create_today.return_value = mission
        mock_trust_level_service.get_my_level.return_value = trust_level
        mock_flashcard_service.get_due_cards.return_value = ([], 0)
        mock_streak_service.get_streak.return_value = streak_resp

        result = await daily_service.get_daily_summary(
            user_id=user_id, org_id=org_id, token="tok",
        )

        assert result.streak_days == 0
        assert "Git" in result.greeting

    async def test_calls_services_in_parallel(
        self,
        daily_service,
        mock_mission_service,
        mock_trust_level_service,
        mock_flashcard_service,
        mock_streak_service,
        user_id,
        org_id,
    ):
        """Verify all 4 sub-services are called."""
        mission = _make_mission(user_id, org_id)
        trust_level = _make_trust_level(user_id, org_id)
        streak_resp = StreakResponse(
            current_streak=1,
            longest_streak=1,
            last_activity_date=None,
            active_today=True,
        )

        mock_mission_service.get_or_create_today.return_value = mission
        mock_trust_level_service.get_my_level.return_value = trust_level
        mock_flashcard_service.get_due_cards.return_value = ([], 2)
        mock_streak_service.get_streak.return_value = streak_resp

        await daily_service.get_daily_summary(
            user_id=user_id, org_id=org_id, token="tok",
        )

        mock_mission_service.get_or_create_today.assert_awaited_once_with(
            user_id, org_id, token="tok",
        )
        mock_trust_level_service.get_my_level.assert_awaited_once_with(user_id, org_id)
        mock_flashcard_service.get_due_cards.assert_awaited_once_with(user_id)
        mock_streak_service.get_streak.assert_awaited_once_with(user_id)
