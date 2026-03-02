import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.notification import Notification, NotificationType
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_send_flashcard_reminders_creates_notifications(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1, user2 = uuid4(), uuid4()
    mock_repo.has_unread_by_type.return_value = False
    mock_repo.create.side_effect = [
        Notification(
            id=uuid4(), user_id=uid,
            type=NotificationType.FLASHCARD_REMINDER,
            title="Flashcards due for review!",
            body=f"You have {count} flashcards due for review!",
            is_read=False,
            created_at=None,
        )
        for uid, count in [(user1, 5), (user2, 3)]
    ]

    count = await notification_service.send_flashcard_reminders(
        [{"user_id": user1, "card_count": 5}, {"user_id": user2, "card_count": 3}]
    )

    assert count == 2
    assert mock_repo.create.call_count == 2
    mock_repo.create.assert_any_call(
        user1,
        NotificationType.FLASHCARD_REMINDER,
        "Flashcards due for review!",
        "You have 5 flashcards due for review!",
    )
    mock_repo.create.assert_any_call(
        user2,
        NotificationType.FLASHCARD_REMINDER,
        "Flashcards due for review!",
        "You have 3 flashcards due for review!",
    )


@pytest.mark.asyncio
async def test_send_flashcard_reminders_empty_list(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    count = await notification_service.send_flashcard_reminders([])

    assert count == 0
    mock_repo.create.assert_not_called()
    mock_repo.has_unread_by_type.assert_not_called()


@pytest.mark.asyncio
async def test_send_flashcard_reminders_skips_duplicates(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1 = uuid4()
    mock_repo.has_unread_by_type.return_value = True

    count = await notification_service.send_flashcard_reminders(
        [{"user_id": user1, "card_count": 5}]
    )

    assert count == 0
    mock_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_send_flashcard_reminders_sends_when_no_existing(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    user1 = uuid4()
    mock_repo.has_unread_by_type.return_value = False
    mock_repo.create.return_value = Notification(
        id=uuid4(), user_id=user1,
        type=NotificationType.FLASHCARD_REMINDER,
        title="Flashcards due for review!",
        body="You have 10 flashcards due for review!",
        is_read=False,
        created_at=None,
    )

    count = await notification_service.send_flashcard_reminders(
        [{"user_id": user1, "card_count": 10}]
    )

    assert count == 1
    mock_repo.create.assert_called_once()
