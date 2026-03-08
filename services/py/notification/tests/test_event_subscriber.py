from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.notification import Notification, NotificationType
from app.services.event_subscriber import NotificationEventSubscriber
from app.services.notification_service import NotificationService


def _make_msg(data: dict) -> MagicMock:
    msg = MagicMock()
    msg.data = json.dumps(data).encode()
    msg.ack = AsyncMock()
    return msg


def _make_notification(user_id, ntype: NotificationType) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=user_id,
        type=ntype,
        title="Test",
        body="Test body",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_notification_service():
    svc = AsyncMock(spec=NotificationService)
    svc.create.return_value = None
    return svc


@pytest.fixture
def mock_nats_client():
    client = AsyncMock()
    client.subscribe = AsyncMock()
    return client


@pytest.fixture
def subscriber(mock_nats_client, mock_notification_service):
    return NotificationEventSubscriber(
        nats_client=mock_nats_client,
        notification_service=mock_notification_service,
    )


class TestNotificationEventSubscriber:
    async def test_start_registers_subscriptions(
        self, subscriber, mock_nats_client
    ) -> None:
        await subscriber.start()

        assert mock_nats_client.subscribe.call_count == 3
        subjects = [
            call.kwargs["subject"] if "subject" in call.kwargs else call.args[0]
            for call in mock_nats_client.subscribe.call_args_list
        ]
        assert "platform.mission.completed" in subjects
        assert "platform.badge.earned" in subjects
        assert "platform.streak.milestone" in subjects

    async def test_mission_completed_creates_notification(
        self, subscriber, mock_notification_service
    ) -> None:
        user_id = uuid4()
        event_id = str(uuid4())
        msg = _make_msg({
            "event_id": event_id,
            "user_id": str(user_id),
            "organization_id": "",
            "mission_id": str(uuid4()),
            "score": 0.85,
            "timestamp": "2026-03-08T10:00:00Z",
        })

        await subscriber._handle_mission_completed(msg)

        mock_notification_service.create.assert_called_once()
        call_kwargs = mock_notification_service.create.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["type"] == NotificationType.MISSION_COMPLETED
        assert "Mission completed" in call_kwargs["title"]
        assert call_kwargs["event_id"] == event_id
        msg.ack.assert_called_once()

    async def test_badge_earned_creates_notification(
        self, subscriber, mock_notification_service
    ) -> None:
        user_id = uuid4()
        event_id = str(uuid4())
        msg = _make_msg({
            "event_id": event_id,
            "user_id": str(user_id),
            "badge_type": "streak_7",
            "timestamp": "2026-03-08T10:00:00Z",
        })

        await subscriber._handle_badge_earned(msg)

        mock_notification_service.create.assert_called_once()
        call_kwargs = mock_notification_service.create.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["type"] == NotificationType.BADGE_EARNED
        assert "badge" in call_kwargs["title"].lower()
        assert call_kwargs["event_id"] == event_id
        msg.ack.assert_called_once()

    async def test_streak_milestone_creates_notification(
        self, subscriber, mock_notification_service
    ) -> None:
        user_id = uuid4()
        event_id = str(uuid4())
        msg = _make_msg({
            "event_id": event_id,
            "user_id": str(user_id),
            "streak": 7,
            "timestamp": "2026-03-08T10:00:00Z",
        })

        await subscriber._handle_streak_milestone(msg)

        mock_notification_service.create.assert_called_once()
        call_kwargs = mock_notification_service.create.call_args.kwargs
        assert call_kwargs["user_id"] == user_id
        assert call_kwargs["type"] == NotificationType.STREAK_MILESTONE
        assert "7" in call_kwargs["title"]
        assert call_kwargs["event_id"] == event_id
        msg.ack.assert_called_once()

    async def test_duplicate_event_skipped(
        self, subscriber, mock_notification_service
    ) -> None:
        user_id = uuid4()
        event_id = str(uuid4())
        # service.create returns None when dedup fires (idempotent)
        mock_notification_service.create.return_value = None

        msg = _make_msg({
            "event_id": event_id,
            "user_id": str(user_id),
            "organization_id": "",
            "mission_id": str(uuid4()),
            "score": 0.9,
            "timestamp": "2026-03-08T10:00:00Z",
        })

        # Call twice simulating duplicate delivery
        await subscriber._handle_mission_completed(msg)
        await subscriber._handle_mission_completed(msg)

        # create called twice — dedup logic lives in NotificationService
        assert mock_notification_service.create.call_count == 2
        # ack still called both times (at-least-once delivery)
        assert msg.ack.call_count == 2

    async def test_invalid_json_gracefully_ignored(
        self, subscriber, mock_notification_service
    ) -> None:
        msg = MagicMock()
        msg.data = b"not valid json {{{"
        msg.ack = AsyncMock()

        # Must not raise
        await subscriber._handle_mission_completed(msg)
        await subscriber._handle_badge_earned(msg)
        await subscriber._handle_streak_milestone(msg)

        mock_notification_service.create.assert_not_called()

    async def test_missing_fields_gracefully_ignored(
        self, subscriber, mock_notification_service
    ) -> None:
        msg = _make_msg({})  # empty payload

        await subscriber._handle_mission_completed(msg)
        await subscriber._handle_badge_earned(msg)
        await subscriber._handle_streak_milestone(msg)

        mock_notification_service.create.assert_not_called()
