"""TDD tests for MasteryUpdated NATS event publishing.

RED phase: these tests are written BEFORE implementation.
They verify that ConceptService publishes a MasteryUpdated event
to NATS after applying a mastery delta.
"""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.concept import ConceptMastery
from app.domain.events import MasteryUpdated
from app.repositories.concept_repo import ConceptRepository
from app.services.concept_service import ConceptService
from common.nats import NATSClient


@pytest.fixture
def mock_concept_repo():
    return AsyncMock(spec=ConceptRepository)


@pytest.fixture
def mock_nats():
    return AsyncMock(spec=NATSClient)


@pytest.fixture
def student_id():
    return uuid4()


@pytest.fixture
def concept_id():
    return uuid4()


def _make_mastery(student_id, concept_id, mastery: float) -> ConceptMastery:
    return ConceptMastery(
        id=uuid4(),
        student_id=student_id,
        concept_id=concept_id,
        mastery=mastery,
        updated_at=datetime.now(timezone.utc),
    )


class TestMasteryUpdatedDataclass:
    """MasteryUpdated domain event is a frozen dataclass."""

    def test_mastery_updated_has_required_fields(self):
        org_id = str(uuid4())
        user_id = str(uuid4())
        concept_id = str(uuid4())
        event = MasteryUpdated(
            user_id=user_id,
            organization_id=org_id,
            concept_id=concept_id,
            new_level=0.75,
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.user_id == user_id
        assert event.organization_id == org_id
        assert event.concept_id == concept_id
        assert event.new_level == 0.75
        assert event.timestamp == "2026-01-01T00:00:00Z"

    def test_mastery_updated_is_immutable(self):
        event = MasteryUpdated(
            user_id="u1",
            organization_id="o1",
            concept_id="c1",
            new_level=0.5,
            timestamp="2026-01-01T00:00:00Z",
        )
        with pytest.raises(Exception):
            event.new_level = 0.9  # type: ignore[misc]


class TestApplyMasteryDeltaPublishesEvent:
    """ConceptService publishes MasteryUpdated to NATS after mastery delta."""

    async def test_publishes_to_correct_subject(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        """Event is published to 'platform.mastery.updated' subject."""
        mock_concept_repo.get_mastery.return_value = _make_mastery(student_id, concept_id, 0.3)
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.45)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.15, organization_id="org-abc"
        )

        mock_nats.publish.assert_called_once()
        subject = mock_nats.publish.call_args[0][0]
        assert subject == "platform.mastery.updated"

    async def test_event_payload_contains_user_id(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.2)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.2, organization_id="org-xyz"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["user_id"] == str(student_id)

    async def test_event_payload_contains_organization_id(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        org_id = "org-" + str(uuid4())
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.1, organization_id=org_id
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["organization_id"] == org_id

    async def test_event_payload_contains_concept_id(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.3)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.3, organization_id="org-1"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["concept_id"] == str(concept_id)

    async def test_event_payload_new_level_is_computed_value(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        """new_level reflects the value after delta is applied (base + delta)."""
        mock_concept_repo.get_mastery.return_value = _make_mastery(student_id, concept_id, 0.3)
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.45)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.15, organization_id="org-1"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["new_level"] == pytest.approx(0.45)

    async def test_event_payload_new_level_when_no_prior_mastery(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        """When no prior mastery record exists, base is 0.0."""
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.2)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.2, organization_id="org-1"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["new_level"] == pytest.approx(0.2)

    async def test_event_payload_contains_timestamp(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.1, organization_id="org-1"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert "timestamp" in event
        assert event["timestamp"]  # non-empty

    async def test_event_payload_is_valid_bytes(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(
            student_id, concept_id, 0.1, organization_id="org-1"
        )

        _, payload_bytes = mock_nats.publish.call_args[0]
        assert isinstance(payload_bytes, bytes)
        # Must be valid JSON
        json.loads(payload_bytes)


class TestMasteryUpdateRobustness:
    """NATS failures and missing client do not break mastery persistence."""

    async def test_nats_failure_does_not_abort_mastery_update(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        """If NATS publish raises, mastery DB write still succeeds."""
        mock_nats.publish.side_effect = RuntimeError("NATS disconnected")
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)

        # Must not raise — mastery is more important than event publishing
        await service.apply_mastery_delta(student_id, concept_id, 0.1)

        mock_concept_repo.upsert_mastery.assert_called_once()

    async def test_no_nats_call_when_client_is_none(
        self, mock_concept_repo, student_id, concept_id
    ):
        """Service without NATSClient is backward-compatible — no error raised."""
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo)  # no nats_client

        await service.apply_mastery_delta(student_id, concept_id, 0.1)

        mock_concept_repo.upsert_mastery.assert_called_once()

    async def test_organization_id_defaults_to_empty_string_when_not_provided(
        self, mock_concept_repo, mock_nats, student_id, concept_id
    ):
        """When organization_id not passed, event still publishes with empty string."""
        mock_concept_repo.get_mastery.return_value = None
        mock_concept_repo.upsert_mastery.return_value = _make_mastery(student_id, concept_id, 0.1)

        service = ConceptService(repo=mock_concept_repo, nats_client=mock_nats)
        await service.apply_mastery_delta(student_id, concept_id, 0.1)

        mock_nats.publish.assert_called_once()
        _, payload_bytes = mock_nats.publish.call_args[0]
        event = json.loads(payload_bytes)
        assert event["organization_id"] == ""
