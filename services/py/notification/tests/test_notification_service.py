import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import NotFoundError
from app.domain.notification import Notification, NotificationType
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_create_notification(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
    sample_notification: Notification,
    user_id,
):
    mock_repo.create.return_value = sample_notification

    result = await notification_service.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="You enrolled in Python 101",
        body="Welcome to the course!",
    )

    assert result.id == sample_notification.id
    assert result.title == "You enrolled in Python 101"
    mock_repo.create.assert_called_once_with(
        user_id, NotificationType.ENROLLMENT,
        "You enrolled in Python 101", "Welcome to the course!", False, None,
        event_id=None,
    )


@pytest.mark.asyncio
async def test_list_my(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
    sample_notification: Notification,
    user_id,
):
    mock_repo.list_by_user.return_value = ([sample_notification], 1)

    items, total = await notification_service.list_my(user_id, limit=20, offset=0)

    assert len(items) == 1
    assert total == 1
    mock_repo.list_by_user.assert_called_once_with(user_id, 20, 0)


@pytest.mark.asyncio
async def test_mark_as_read_success(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
    sample_notification: Notification,
    notification_id,
    user_id,
):
    mock_repo.get_by_id.return_value = sample_notification
    read_notification = Notification(
        id=notification_id,
        user_id=user_id,
        type=sample_notification.type,
        title=sample_notification.title,
        body=sample_notification.body,
        is_read=True,
        created_at=sample_notification.created_at,
    )
    mock_repo.mark_as_read.return_value = read_notification

    result = await notification_service.mark_as_read(notification_id, user_id)

    assert result.is_read is True
    mock_repo.mark_as_read.assert_called_once_with(notification_id)


@pytest.mark.asyncio
async def test_mark_as_read_not_found(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
):
    mock_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Notification not found"):
        await notification_service.mark_as_read(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_mark_as_read_wrong_user(
    notification_service: NotificationService,
    mock_repo: AsyncMock,
    sample_notification: Notification,
    notification_id,
):
    mock_repo.get_by_id.return_value = sample_notification

    with pytest.raises(NotFoundError, match="Notification not found"):
        await notification_service.mark_as_read(notification_id, uuid4())
