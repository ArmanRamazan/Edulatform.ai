import pytest
from unittest.mock import AsyncMock, call
from uuid import uuid4

from app.domain.notification import Notification, NotificationType
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_send_streak_reminders_creates_notifications(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1, user2 = uuid4(), uuid4()
    mock_repo.has_unread_by_type.return_value = False
    mock_repo.create.side_effect = [
        Notification(
            id=uuid4(), user_id=uid,
            type=NotificationType.STREAK_REMINDER,
            title="Your streak is at risk!",
            body="You haven't studied today. Keep your streak alive!",
            is_read=False,
            created_at=None,
        )
        for uid in [user1, user2]
    ]

    count = await notification_service.send_streak_reminders([user1, user2])

    assert count == 2
    assert mock_repo.create.call_count == 2
    mock_repo.create.assert_any_call(
        user1,
        NotificationType.STREAK_REMINDER,
        "Your streak is at risk!",
        "You haven't studied today. Keep your streak alive!",
    )
    mock_repo.create.assert_any_call(
        user2,
        NotificationType.STREAK_REMINDER,
        "Your streak is at risk!",
        "You haven't studied today. Keep your streak alive!",
    )


@pytest.mark.asyncio
async def test_send_streak_reminders_empty_list(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    count = await notification_service.send_streak_reminders([])

    assert count == 0
    mock_repo.create.assert_not_called()
    mock_repo.has_unread_by_type.assert_not_called()


@pytest.mark.asyncio
async def test_send_streak_reminders_skips_duplicates(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1 = uuid4()
    mock_repo.has_unread_by_type.return_value = True

    count = await notification_service.send_streak_reminders([user1])

    assert count == 0
    mock_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_send_streak_reminders_sends_when_no_existing(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1 = uuid4()
    mock_repo.has_unread_by_type.return_value = False
    mock_repo.create.return_value = Notification(
        id=uuid4(), user_id=user1,
        type=NotificationType.STREAK_REMINDER,
        title="Your streak is at risk!",
        body="You haven't studied today. Keep your streak alive!",
        is_read=False,
        created_at=None,
    )

    count = await notification_service.send_streak_reminders([user1])

    assert count == 1
    mock_repo.create.assert_called_once()
