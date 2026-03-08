"""TDD tests for NATS event publishing in Learning service.

RED phase: these tests are written BEFORE implementation.
They verify that MissionService, BadgeService, and StreakService
publish the correct events to NATS subjects.
"""
import json
from datetime import datetime, timezone, timedelta, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import httpx

from app.domain.badge import Badge
from app.domain.mission import Mission
from app.domain.streak import Streak
from app.repositories.badge_repo import BadgeRepository
from app.repositories.mission_repo import MissionRepository
from app.repositories.streak_repo import StreakRepository
from app.services.badge_service import BadgeService
from app.services.mission_service import MissionService
from app.services.streak_service import StreakService
from common.nats import NATSClient


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_mission(
    mission_id: UUID,
    user_id: UUID,
    org_id: UUID,
    status: str = "in_progress",
    concept_id: UUID | None = None,
) -> Mission:
    return Mission(
        id=mission_id,
        user_id=user_id,
        organization_id=org_id,
        concept_id=concept_id,
        mission_type="daily",
        status=status,
        blueprint={},
        score=None,
        mastery_delta=None,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


def _make_completed_mission(
    mission_id: UUID,
    user_id: UUID,
    org_id: UUID,
    score: float = 0.85,
) -> Mission:
    return Mission(
        id=mission_id,
        user_id=user_id,
        organization_id=org_id,
        concept_id=None,
        mission_type="daily",
        status="completed",
        blueprint={},
        score=score,
        mastery_delta=0.0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


def _make_badge(user_id: UUID, badge_type: str = "streak_7") -> Badge:
    return Badge(
        id=uuid4(),
        user_id=user_id,
        badge_type=badge_type,
        unlocked_at=datetime.now(timezone.utc),
    )


def _make_streak(user_id: UUID, current: int) -> Streak:
    return Streak(
        user_id=user_id,
        current_streak=current,
        longest_streak=current,
        last_activity_date=date.today(),
        updated_at=datetime.now(timezone.utc),
    )


def _make_mission_service(
    mission_repo: AsyncMock,
    nats_client: AsyncMock | None = None,
) -> MissionService:
    mock_trust = AsyncMock()
    mock_trust.record_mission_completed = AsyncMock()
    mock_concept = AsyncMock()
    mock_concept.apply_mastery_delta = AsyncMock()
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_settings = MagicMock()
    mock_settings.ai_service_url = "http://ai:8006"
    return MissionService(
        mission_repo=mission_repo,
        trust_level_service=mock_trust,
        http_client=mock_http,
        settings=mock_settings,
        concept_service=mock_concept,
        nats_client=nats_client,
    )


# ---------------------------------------------------------------------------
# TestMissionCompletedEvent
# ---------------------------------------------------------------------------

class TestMissionCompletedEvent:
    """MissionService publishes platform.mission.completed after complete_mission."""

    async def test_publishes_to_correct_subject(self):
        """complete_mission publishes to 'platform.mission.completed'."""
        user_id = uuid4()
        org_id = uuid4()
        mission_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=MissionRepository)
        mock_repo.get_by_id.return_value = _make_mission(mission_id, user_id, org_id)
        completed = _make_completed_mission(mission_id, user_id, org_id, score=0.85)
        mock_repo.update_status.return_value = completed

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = AsyncMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"score": 0.85, "mastery_delta": 0.0}),
        )

        mock_trust = AsyncMock()
        mock_trust.record_mission_completed = AsyncMock()
        mock_concept = AsyncMock()
        mock_concept.apply_mastery_delta = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ai_service_url = "http://ai:8006"

        service = MissionService(
            mission_repo=mock_repo,
            trust_level_service=mock_trust,
            http_client=mock_http,
            settings=mock_settings,
            concept_service=mock_concept,
            nats_client=mock_nats,
        )

        await service.complete_mission(mission_id, user_id, "session-abc", token="tok")

        mock_nats.publish.assert_called_once()
        subject = mock_nats.publish.call_args[0][0]
        assert subject == "platform.mission.completed"

    async def test_payload_has_correct_fields(self):
        """Published payload contains event_id, user_id, organization_id, mission_id, score, timestamp."""
        user_id = uuid4()
        org_id = uuid4()
        mission_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=MissionRepository)
        mock_repo.get_by_id.return_value = _make_mission(mission_id, user_id, org_id)
        completed = _make_completed_mission(mission_id, user_id, org_id, score=0.85)
        mock_repo.update_status.return_value = completed

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = AsyncMock(
            status_code=200,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"score": 0.85, "mastery_delta": 0.0}),
        )

        mock_trust = AsyncMock()
        mock_trust.record_mission_completed = AsyncMock()
        mock_concept = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ai_service_url = "http://ai:8006"

        service = MissionService(
            mission_repo=mock_repo,
            trust_level_service=mock_trust,
            http_client=mock_http,
            settings=mock_settings,
            concept_service=mock_concept,
            nats_client=mock_nats,
        )

        await service.complete_mission(mission_id, user_id, "session-abc", token="tok")

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert "event_id" in event
        assert event["user_id"] == str(user_id)
        assert event["organization_id"] == str(org_id)
        assert event["mission_id"] == str(mission_id)
        assert event["score"] == pytest.approx(0.85)
        assert "timestamp" in event

    async def test_event_id_is_valid_uuid(self):
        """event_id in payload is a valid UUID string."""
        user_id = uuid4()
        org_id = uuid4()
        mission_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=MissionRepository)
        mock_repo.get_by_id.return_value = _make_mission(mission_id, user_id, org_id)
        mock_repo.update_status.return_value = _make_completed_mission(mission_id, user_id, org_id)

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = AsyncMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"score": 0.9, "mastery_delta": 0.0}),
        )

        mock_trust = AsyncMock()
        mock_trust.record_mission_completed = AsyncMock()
        mock_concept = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ai_service_url = "http://ai:8006"

        service = MissionService(
            mission_repo=mock_repo,
            trust_level_service=mock_trust,
            http_client=mock_http,
            settings=mock_settings,
            concept_service=mock_concept,
            nats_client=mock_nats,
        )

        await service.complete_mission(mission_id, user_id, "session-abc", token="tok")

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        # Must be parseable as UUID
        UUID(event["event_id"])

    async def test_nats_failure_does_not_abort_mission(self):
        """If NATS publish raises, complete_mission still returns completed mission."""
        user_id = uuid4()
        org_id = uuid4()
        mission_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_nats.publish.side_effect = RuntimeError("NATS disconnected")
        mock_repo = AsyncMock(spec=MissionRepository)
        mock_repo.get_by_id.return_value = _make_mission(mission_id, user_id, org_id)
        completed = _make_completed_mission(mission_id, user_id, org_id)
        mock_repo.update_status.return_value = completed

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = AsyncMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"score": 0.7, "mastery_delta": 0.0}),
        )

        mock_trust = AsyncMock()
        mock_trust.record_mission_completed = AsyncMock()
        mock_concept = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ai_service_url = "http://ai:8006"

        service = MissionService(
            mission_repo=mock_repo,
            trust_level_service=mock_trust,
            http_client=mock_http,
            settings=mock_settings,
            concept_service=mock_concept,
            nats_client=mock_nats,
        )

        result = await service.complete_mission(mission_id, user_id, "session-abc", token="tok")

        assert result.status == "completed"

    async def test_no_publish_when_nats_client_is_none(self):
        """When nats_client=None, no publish attempt is made, mission still completes."""
        user_id = uuid4()
        org_id = uuid4()
        mission_id = uuid4()
        mock_repo = AsyncMock(spec=MissionRepository)
        mock_repo.get_by_id.return_value = _make_mission(mission_id, user_id, org_id)
        completed = _make_completed_mission(mission_id, user_id, org_id)
        mock_repo.update_status.return_value = completed

        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post.return_value = AsyncMock(
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"score": 0.6, "mastery_delta": 0.0}),
        )

        mock_trust = AsyncMock()
        mock_trust.record_mission_completed = AsyncMock()
        mock_concept = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.ai_service_url = "http://ai:8006"

        service = MissionService(
            mission_repo=mock_repo,
            trust_level_service=mock_trust,
            http_client=mock_http,
            settings=mock_settings,
            concept_service=mock_concept,
            # nats_client not provided → defaults to None
        )

        result = await service.complete_mission(mission_id, user_id, "session-abc", token="tok")

        assert result.status == "completed"


# ---------------------------------------------------------------------------
# TestBadgeEarnedEvent
# ---------------------------------------------------------------------------

class TestBadgeEarnedEvent:
    """BadgeService publishes platform.badge.earned after try_unlock."""

    async def test_publishes_to_correct_subject(self):
        """try_unlock publishes to 'platform.badge.earned'."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=BadgeRepository)
        mock_repo.create.return_value = _make_badge(user_id, "streak_7")

        service = BadgeService(repo=mock_repo, nats_client=mock_nats)
        await service.try_unlock(user_id, "streak_7")

        mock_nats.publish.assert_called_once()
        subject = mock_nats.publish.call_args[0][0]
        assert subject == "platform.badge.earned"

    async def test_payload_has_correct_fields(self):
        """Published payload contains event_id, user_id, badge_type, timestamp."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=BadgeRepository)
        mock_repo.create.return_value = _make_badge(user_id, "streak_7")

        service = BadgeService(repo=mock_repo, nats_client=mock_nats)
        await service.try_unlock(user_id, "streak_7")

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert "event_id" in event
        assert event["user_id"] == str(user_id)
        assert event["badge_type"] == "streak_7"
        assert "timestamp" in event
        assert event["timestamp"]

    async def test_nats_failure_does_not_abort_badge_creation(self):
        """If NATS publish raises, try_unlock still returns badge."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_nats.publish.side_effect = RuntimeError("NATS unavailable")
        mock_repo = AsyncMock(spec=BadgeRepository)
        expected_badge = _make_badge(user_id, "quiz_ace")
        mock_repo.create.return_value = expected_badge

        service = BadgeService(repo=mock_repo, nats_client=mock_nats)
        result = await service.try_unlock(user_id, "quiz_ace")

        assert result == expected_badge

    async def test_no_publish_when_nats_client_is_none(self):
        """When nats_client=None, no publish attempt is made, badge still returned."""
        user_id = uuid4()
        mock_repo = AsyncMock(spec=BadgeRepository)
        expected_badge = _make_badge(user_id, "streak_7")
        mock_repo.create.return_value = expected_badge

        service = BadgeService(repo=mock_repo)  # no nats_client
        result = await service.try_unlock(user_id, "streak_7")

        assert result == expected_badge

    async def test_payload_is_valid_bytes(self):
        """Payload is bytes and parses as valid JSON."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=BadgeRepository)
        mock_repo.create.return_value = _make_badge(user_id, "streak_7")

        service = BadgeService(repo=mock_repo, nats_client=mock_nats)
        await service.try_unlock(user_id, "streak_7")

        _, payload_bytes = mock_nats.publish.call_args[0]
        assert isinstance(payload_bytes, bytes)
        json.loads(payload_bytes)  # must not raise


# ---------------------------------------------------------------------------
# TestStreakMilestoneEvent
# ---------------------------------------------------------------------------

class TestStreakMilestoneEvent:
    """StreakService publishes platform.streak.milestone on milestone streaks."""

    async def test_publishes_when_streak_hits_milestone(self):
        """record_activity publishes to 'platform.streak.milestone' when streak = 7."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=StreakRepository)
        # Simulate: had streak of 6 yesterday → today becomes 7 (milestone)
        yesterday_streak = Streak(
            user_id=user_id,
            current_streak=6,
            longest_streak=6,
            last_activity_date=date.today() - timedelta(days=1),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repo.get_by_user.return_value = yesterday_streak
        mock_repo.upsert.return_value = _make_streak(user_id, 7)

        service = StreakService(repo=mock_repo, nats_client=mock_nats)
        await service.record_activity(user_id)

        mock_nats.publish.assert_called_once()
        subject = mock_nats.publish.call_args[0][0]
        assert subject == "platform.streak.milestone"

    async def test_payload_has_correct_fields(self):
        """Published payload contains event_id, user_id, streak, timestamp."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=StreakRepository)
        yesterday_streak = Streak(
            user_id=user_id,
            current_streak=6,
            longest_streak=6,
            last_activity_date=date.today() - timedelta(days=1),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repo.get_by_user.return_value = yesterday_streak
        mock_repo.upsert.return_value = _make_streak(user_id, 7)

        service = StreakService(repo=mock_repo, nats_client=mock_nats)
        await service.record_activity(user_id)

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert "event_id" in event
        assert event["user_id"] == str(user_id)
        assert event["streak"] == 7
        assert "timestamp" in event
        assert event["timestamp"]

    async def test_no_publish_when_streak_not_milestone(self):
        """No NATS publish when streak is not a milestone (e.g. 3)."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_repo = AsyncMock(spec=StreakRepository)
        yesterday_streak = Streak(
            user_id=user_id,
            current_streak=2,
            longest_streak=2,
            last_activity_date=date.today() - timedelta(days=1),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repo.get_by_user.return_value = yesterday_streak
        mock_repo.upsert.return_value = _make_streak(user_id, 3)

        service = StreakService(repo=mock_repo, nats_client=mock_nats)
        await service.record_activity(user_id)

        mock_nats.publish.assert_not_called()

    async def test_nats_failure_does_not_abort_streak_update(self):
        """If NATS publish raises, record_activity still returns streak."""
        user_id = uuid4()
        mock_nats = AsyncMock(spec=NATSClient)
        mock_nats.publish.side_effect = RuntimeError("NATS down")
        mock_repo = AsyncMock(spec=StreakRepository)
        yesterday_streak = Streak(
            user_id=user_id,
            current_streak=6,
            longest_streak=6,
            last_activity_date=date.today() - timedelta(days=1),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repo.get_by_user.return_value = yesterday_streak
        expected_streak = _make_streak(user_id, 7)
        mock_repo.upsert.return_value = expected_streak

        service = StreakService(repo=mock_repo, nats_client=mock_nats)
        result = await service.record_activity(user_id)

        assert result == expected_streak

    async def test_no_publish_when_nats_client_is_none(self):
        """When nats_client=None, no publish attempt, streak still returned."""
        user_id = uuid4()
        mock_repo = AsyncMock(spec=StreakRepository)
        yesterday_streak = Streak(
            user_id=user_id,
            current_streak=6,
            longest_streak=6,
            last_activity_date=date.today() - timedelta(days=1),
            updated_at=datetime.now(timezone.utc),
        )
        mock_repo.get_by_user.return_value = yesterday_streak
        expected_streak = _make_streak(user_id, 7)
        mock_repo.upsert.return_value = expected_streak

        service = StreakService(repo=mock_repo)  # no nats_client
        result = await service.record_activity(user_id)

        assert result == expected_streak

    async def test_publishes_for_each_milestone_value(self):
        """Publish happens for all milestone values: 14, 30, 60, etc."""
        for milestone in (14, 30, 60, 90, 180, 365):
            user_id = uuid4()
            mock_nats = AsyncMock(spec=NATSClient)
            mock_repo = AsyncMock(spec=StreakRepository)
            yesterday_streak = Streak(
                user_id=user_id,
                current_streak=milestone - 1,
                longest_streak=milestone - 1,
                last_activity_date=date.today() - timedelta(days=1),
                updated_at=datetime.now(timezone.utc),
            )
            mock_repo.get_by_user.return_value = yesterday_streak
            mock_repo.upsert.return_value = _make_streak(user_id, milestone)

            service = StreakService(repo=mock_repo, nats_client=mock_nats)
            await service.record_activity(user_id)

            mock_nats.publish.assert_called_once(), f"Expected publish for milestone {milestone}"
            subject = mock_nats.publish.call_args[0][0]
            assert subject == "platform.streak.milestone"
            _, payload_bytes = mock_nats.publish.call_args[0]
            event = json.loads(payload_bytes)
            assert event["streak"] == milestone
