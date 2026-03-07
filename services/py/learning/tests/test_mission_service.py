from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.concept import CourseMasteryResponse, MasteryResponse
from app.domain.mission import Mission
from app.repositories.mission_repo import MissionRepository
from app.services.concept_service import ConceptService
from app.services.trust_level_service import TrustLevelService
from app.services.mission_service import MissionService
from app.services.review_generator import ReviewGenerator


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_mission_repo():
    return AsyncMock(spec=MissionRepository)


@pytest.fixture
def mock_trust_service():
    return AsyncMock(spec=TrustLevelService)


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def mock_concept_service():
    return AsyncMock(spec=ConceptService)


@pytest.fixture
def settings():
    s = MagicMock()
    s.ai_service_url = "http://localhost:8006"
    return s


@pytest.fixture
def mock_review_generator():
    return AsyncMock(spec=ReviewGenerator)


@pytest.fixture
def mission_service(
    mock_mission_repo, mock_trust_service, mock_http_client,
    mock_review_generator, mock_concept_service, settings,
):
    return MissionService(
        mission_repo=mock_mission_repo,
        trust_level_service=mock_trust_service,
        http_client=mock_http_client,
        settings=settings,
        concept_service=mock_concept_service,
        review_generator=mock_review_generator,
    )


def _make_mission(
    user_id,
    org_id,
    status: str = "pending",
    score: float | None = None,
    mastery_delta: float | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    concept_id=None,
) -> Mission:
    return Mission(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        concept_id=concept_id,
        mission_type="daily",
        status=status,
        blueprint={"topic": "variables", "questions": []},
        score=score,
        mastery_delta=mastery_delta,
        started_at=started_at,
        completed_at=completed_at,
        created_at=datetime.now(timezone.utc),
    )


# --- get_or_create_today ---


class TestGetOrCreateToday:
    async def test_returns_existing_mission(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        existing = _make_mission(user_id, org_id)
        mock_mission_repo.get_today.return_value = existing

        result = await mission_service.get_or_create_today(user_id, org_id, token="tok")

        assert result == existing
        mock_mission_repo.get_today.assert_awaited_once_with(user_id)

    async def test_creates_mission_from_ai_blueprint(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_concept_service, user_id, org_id,
    ):
        mock_mission_repo.get_today.return_value = None
        mock_concept_service.get_course_mastery.return_value = CourseMasteryResponse(
            course_id=org_id, items=[],
        )
        blueprint = {
            "concept_id": str(uuid4()),
            "mission_type": "daily",
            "topic": "variables",
            "questions": [{"q": "What is x?"}],
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = blueprint
        mock_http_client.post.return_value = mock_response

        created = _make_mission(user_id, org_id)
        mock_mission_repo.create.return_value = created

        result = await mission_service.get_or_create_today(user_id, org_id, token="tok")

        assert result == created
        mock_http_client.post.assert_awaited_once()
        mock_mission_repo.create.assert_awaited_once()

    async def test_raises_on_ai_service_failure(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_concept_service, user_id, org_id,
    ):
        mock_mission_repo.get_today.return_value = None
        mock_concept_service.get_course_mastery.return_value = CourseMasteryResponse(
            course_id=org_id, items=[],
        )
        mock_http_client.post.side_effect = Exception("AI service down")

        with pytest.raises(Exception, match="AI service"):
            await mission_service.get_or_create_today(user_id, org_id, token="tok")

    async def test_sends_mastery_in_post_request_body(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_concept_service, user_id, org_id,
    ):
        """Learning must push mastery data to AI — no callback from AI to Learning."""
        concept_id = uuid4()
        mock_mission_repo.get_today.return_value = None
        mock_concept_service.get_course_mastery.return_value = CourseMasteryResponse(
            course_id=org_id,
            items=[MasteryResponse(concept_id=concept_id, concept_name="Variables", mastery=0.6)],
        )
        blueprint = {"concept_id": str(concept_id), "mission_type": "daily"}
        mock_response = MagicMock()
        mock_response.json.return_value = blueprint
        mock_http_client.post.return_value = mock_response
        mock_mission_repo.create.return_value = _make_mission(user_id, org_id)

        await mission_service.get_or_create_today(user_id, org_id, token="tok")

        call_args = mock_http_client.post.call_args
        body = call_args[1]["json"]
        assert body["org_id"] == str(org_id)
        assert len(body["mastery"]) == 1
        assert body["mastery"][0]["concept_id"] == str(concept_id)
        assert body["mastery"][0]["mastery"] == 0.6


# --- start_mission ---


class TestStartMission:
    async def test_starts_mission_successfully(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="pending")
        mock_mission_repo.get_by_id.return_value = mission

        started = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.update_status.return_value = started

        result = await mission_service.start_mission(mission.id, user_id)

        assert result.status == "in_progress"
        mock_mission_repo.update_status.assert_awaited_once()

    async def test_raises_not_found_for_missing_mission(
        self, mission_service, mock_mission_repo, user_id,
    ):
        mock_mission_repo.get_by_id.return_value = None

        from common.errors import NotFoundError
        with pytest.raises(NotFoundError):
            await mission_service.start_mission(uuid4(), user_id)

    async def test_raises_forbidden_for_wrong_user(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        mission = _make_mission(uuid4(), org_id, status="pending")
        mock_mission_repo.get_by_id.return_value = mission

        from common.errors import ForbiddenError
        with pytest.raises(ForbiddenError):
            await mission_service.start_mission(mission.id, user_id)

    async def test_raises_if_already_started(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission

        from common.errors import AppError
        with pytest.raises(AppError, match="already"):
            await mission_service.start_mission(mission.id, user_id)


# --- complete_mission ---


class TestCompleteMission:
    async def test_completes_mission_successfully(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_trust_service, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission

        session_result = {"score": 0.85, "mastery_delta": 0.1}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = session_result
        mock_http_client.post.return_value = mock_response

        completed = _make_mission(
            user_id, org_id, status="completed", score=0.85, mastery_delta=0.1,
        )
        mock_mission_repo.update_status.return_value = completed

        result = await mission_service.complete_mission(
            mission.id, user_id, session_id="sess-123", token="tok",
        )

        assert result.status == "completed"
        assert result.score == 0.85
        mock_http_client.post.assert_awaited_once()
        mock_trust_service.record_mission_completed.assert_awaited_once_with(
            user_id, mission.organization_id,
        )

    async def test_raises_not_found_for_missing_mission(
        self, mission_service, mock_mission_repo, user_id,
    ):
        mock_mission_repo.get_by_id.return_value = None

        from common.errors import NotFoundError
        with pytest.raises(NotFoundError):
            await mission_service.complete_mission(uuid4(), user_id, "sess", token="tok")

    async def test_raises_forbidden_for_wrong_user(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        mission = _make_mission(uuid4(), org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission

        from common.errors import ForbiddenError
        with pytest.raises(ForbiddenError):
            await mission_service.complete_mission(
                mission.id, user_id, "sess", token="tok",
            )

    async def test_raises_if_not_in_progress(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="pending")
        mock_mission_repo.get_by_id.return_value = mission

        from common.errors import AppError
        with pytest.raises(AppError, match="not in progress"):
            await mission_service.complete_mission(
                mission.id, user_id, "sess", token="tok",
            )

    async def test_raises_on_coach_service_failure(
        self, mission_service, mock_mission_repo, mock_http_client, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission
        mock_http_client.post.side_effect = Exception("Coach service down")

        with pytest.raises(Exception, match="Coach service"):
            await mission_service.complete_mission(
                mission.id, user_id, "sess", token="tok",
            )

    async def test_calls_review_generator_after_completion(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_trust_service, mock_review_generator, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission

        session_result = {"score": 0.9, "mastery_delta": 0.15}
        mock_response = MagicMock()
        mock_response.json.return_value = session_result
        mock_http_client.post.return_value = mock_response

        completed = _make_mission(user_id, org_id, status="completed", score=0.9)
        mock_mission_repo.update_status.return_value = completed

        mock_review_generator.generate_from_mission.return_value = [uuid4(), uuid4()]

        result = await mission_service.complete_mission(
            mission.id, user_id, "sess", token="tok",
        )

        assert result.status == "completed"
        mock_review_generator.generate_from_mission.assert_awaited_once_with(
            user_id, completed,
        )

    async def test_review_generator_failure_does_not_break_completion(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_trust_service, mock_review_generator, user_id, org_id,
    ):
        mission = _make_mission(user_id, org_id, status="in_progress")
        mock_mission_repo.get_by_id.return_value = mission

        session_result = {"score": 0.7, "mastery_delta": 0.05}
        mock_response = MagicMock()
        mock_response.json.return_value = session_result
        mock_http_client.post.return_value = mock_response

        completed = _make_mission(user_id, org_id, status="completed", score=0.7)
        mock_mission_repo.update_status.return_value = completed

        mock_review_generator.generate_from_mission.side_effect = Exception("DB down")

        result = await mission_service.complete_mission(
            mission.id, user_id, "sess", token="tok",
        )

        assert result.status == "completed"

    async def test_applies_mastery_delta_locally_after_completion(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_trust_service, mock_concept_service, user_id, org_id,
    ):
        """After completion, Learning must update mastery in its own DB — AI must NOT be called."""
        concept_id = uuid4()
        mission = _make_mission(user_id, org_id, status="in_progress", concept_id=concept_id)
        mock_mission_repo.get_by_id.return_value = mission

        session_result = {"score": 0.85, "mastery_delta": 0.15}
        mock_response = MagicMock()
        mock_response.json.return_value = session_result
        mock_http_client.post.return_value = mock_response

        completed = _make_mission(
            user_id, org_id, status="completed", score=0.85, mastery_delta=0.15,
            concept_id=concept_id,
        )
        mock_mission_repo.update_status.return_value = completed

        await mission_service.complete_mission(mission.id, user_id, "sess-123", token="tok")

        # Mastery delta must be applied locally, not sent back to AI
        mock_concept_service.apply_mastery_delta.assert_awaited_once_with(
            user_id, concept_id, 0.15,
        )

    async def test_skips_mastery_update_when_concept_is_none(
        self, mission_service, mock_mission_repo, mock_http_client,
        mock_trust_service, mock_concept_service, user_id, org_id,
    ):
        """Missions without a concept_id (generic missions) don't need mastery update."""
        mission = _make_mission(user_id, org_id, status="in_progress", concept_id=None)
        mock_mission_repo.get_by_id.return_value = mission

        session_result = {"score": 0.7, "mastery_delta": 0.1}
        mock_response = MagicMock()
        mock_response.json.return_value = session_result
        mock_http_client.post.return_value = mock_response

        completed = _make_mission(user_id, org_id, status="completed", score=0.7)
        mock_mission_repo.update_status.return_value = completed

        await mission_service.complete_mission(mission.id, user_id, "sess-123", token="tok")

        mock_concept_service.apply_mastery_delta.assert_not_called()


# --- get_my_missions ---


class TestGetMyMissions:
    async def test_returns_user_missions(
        self, mission_service, mock_mission_repo, user_id, org_id,
    ):
        missions = [_make_mission(user_id, org_id) for _ in range(3)]
        mock_mission_repo.get_by_user.return_value = missions

        result = await mission_service.get_my_missions(user_id, limit=20, offset=0)

        assert len(result) == 3
        mock_mission_repo.get_by_user.assert_awaited_once_with(user_id, 20, 0)


# --- get_streak ---


class TestGetStreak:
    async def test_returns_streak_count(
        self, mission_service, mock_mission_repo, user_id,
    ):
        mock_mission_repo.get_streak.return_value = 7

        result = await mission_service.get_streak(user_id)

        assert result == 7
        mock_mission_repo.get_streak.assert_awaited_once_with(user_id)
