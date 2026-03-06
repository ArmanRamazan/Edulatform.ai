import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx

from app.adapters.ws_client import WsPublisher
from app.domain.notification import Notification, NotificationType
from app.domain.messaging import Message
from app.repositories.notification_repo import NotificationRepository
from app.services.notification_service import NotificationService
from app.services.messaging_service import MessagingService
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.domain.messaging import Conversation


@pytest.fixture
def mock_http_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    response = AsyncMock()
    response.status_code = 200
    client.post.return_value = response
    return client


@pytest.fixture
def ws_publisher(mock_http_client):
    return WsPublisher(
        http_client=mock_http_client,
        ws_gateway_url="http://localhost:8011",
    )


# --- WsPublisher unit tests ---


@pytest.mark.asyncio
async def test_ws_publisher_publishes_notification(mock_http_client, ws_publisher):
    user_id = uuid4()
    notification_data = {
        "id": str(uuid4()),
        "notification_type": "enrollment",
        "title": "Enrolled",
        "body": "Welcome!",
    }

    await ws_publisher.publish_notification(str(user_id), notification_data)

    mock_http_client.post.assert_called_once_with(
        "http://localhost:8011/publish",
        json={
            "target": f"user:{user_id}",
            "message": {
                "type": "notification",
                **notification_data,
            },
        },
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_ws_publisher_fire_and_forget_on_error(mock_http_client, ws_publisher):
    """WsPublisher should not raise even if the gateway is down."""
    mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")
    user_id = uuid4()
    notification_data = {
        "id": str(uuid4()),
        "notification_type": "enrollment",
        "title": "Enrolled",
        "body": "Welcome!",
    }

    # Should not raise
    await ws_publisher.publish_notification(str(user_id), notification_data)


@pytest.mark.asyncio
async def test_ws_publisher_fire_and_forget_on_timeout(mock_http_client, ws_publisher):
    """WsPublisher should not raise on timeout."""
    mock_http_client.post.side_effect = httpx.TimeoutException("Timed out")

    await ws_publisher.publish_notification(
        str(uuid4()),
        {"id": str(uuid4()), "notification_type": "payment", "title": "Paid", "body": "Done"},
    )


# --- NotificationService integration with WsPublisher ---


@pytest.mark.asyncio
async def test_notification_service_publishes_via_ws(mock_http_client):
    """After creating a notification, service should publish via WsPublisher."""
    mock_repo = AsyncMock(spec=NotificationRepository)
    user_id = uuid4()
    notif_id = uuid4()
    notification = Notification(
        id=notif_id,
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Enrolled in Python 101",
        body="Welcome!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.create.return_value = notification

    ws_publisher = WsPublisher(
        http_client=mock_http_client,
        ws_gateway_url="http://localhost:8011",
    )

    service = NotificationService(repo=mock_repo, ws_publisher=ws_publisher)
    await service.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Enrolled in Python 101",
        body="Welcome!",
    )

    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args
    payload = call_kwargs.kwargs["json"] if "json" in call_kwargs.kwargs else call_kwargs[1]["json"]
    assert payload["target"] == f"user:{user_id}"
    assert payload["message"]["type"] == "notification"
    assert payload["message"]["id"] == str(notif_id)
    assert payload["message"]["notification_type"] == "enrollment"
    assert payload["message"]["title"] == "Enrolled in Python 101"


@pytest.mark.asyncio
async def test_notification_service_works_without_ws_publisher():
    """Service should work fine when ws_publisher is None."""
    mock_repo = AsyncMock(spec=NotificationRepository)
    user_id = uuid4()
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Test",
        body="Body",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.create.return_value = notification

    service = NotificationService(repo=mock_repo)
    result = await service.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Test",
        body="Body",
    )

    assert result.id == notification.id


@pytest.mark.asyncio
async def test_notification_service_continues_if_ws_fails(mock_http_client):
    """If WS gateway is down, notification is still created successfully."""
    mock_repo = AsyncMock(spec=NotificationRepository)
    mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

    user_id = uuid4()
    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Test",
        body="Body",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.create.return_value = notification

    ws_publisher = WsPublisher(
        http_client=mock_http_client,
        ws_gateway_url="http://localhost:8011",
    )
    service = NotificationService(repo=mock_repo, ws_publisher=ws_publisher)

    result = await service.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Test",
        body="Body",
    )

    # Notification should still be returned from DB
    assert result.id == notification.id
    mock_repo.create.assert_called_once()


# --- MessagingService integration with WsPublisher ---


@pytest.mark.asyncio
async def test_messaging_service_publishes_via_ws(mock_http_client):
    """After sending a message, service should publish via WsPublisher."""
    mock_conv_repo = AsyncMock(spec=ConversationRepository)
    mock_msg_repo = AsyncMock(spec=MessageRepository)

    sender_id = uuid4()
    recipient_id = uuid4()
    conv_id = uuid4()
    msg_id = uuid4()

    conversation = Conversation(
        id=conv_id,
        participant_1=min(sender_id, recipient_id),
        participant_2=max(sender_id, recipient_id),
        created_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )
    message = Message(
        id=msg_id,
        conversation_id=conv_id,
        sender_id=sender_id,
        content="Hello!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_conv_repo.get_or_create.return_value = conversation
    mock_msg_repo.create_message.return_value = message

    ws_publisher = WsPublisher(
        http_client=mock_http_client,
        ws_gateway_url="http://localhost:8011",
    )

    service = MessagingService(
        conversation_repo=mock_conv_repo,
        message_repo=mock_msg_repo,
        ws_publisher=ws_publisher,
    )

    await service.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="Hello!",
    )

    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args
    payload = call_kwargs.kwargs["json"] if "json" in call_kwargs.kwargs else call_kwargs[1]["json"]
    assert payload["target"] == f"user:{recipient_id}"
    assert payload["message"]["type"] == "notification"
    assert payload["message"]["notification_type"] == "direct_message"
    assert payload["message"]["title"] == "New message"
    assert payload["message"]["body"] == "Hello!"


@pytest.mark.asyncio
async def test_messaging_service_works_without_ws_publisher():
    """MessagingService should work fine when ws_publisher is None."""
    mock_conv_repo = AsyncMock(spec=ConversationRepository)
    mock_msg_repo = AsyncMock(spec=MessageRepository)

    sender_id = uuid4()
    recipient_id = uuid4()
    conv_id = uuid4()

    conversation = Conversation(
        id=conv_id,
        participant_1=min(sender_id, recipient_id),
        participant_2=max(sender_id, recipient_id),
        created_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )
    message = Message(
        id=uuid4(),
        conversation_id=conv_id,
        sender_id=sender_id,
        content="Hello!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_conv_repo.get_or_create.return_value = conversation
    mock_msg_repo.create_message.return_value = message

    service = MessagingService(
        conversation_repo=mock_conv_repo,
        message_repo=mock_msg_repo,
    )

    result = await service.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="Hello!",
    )
    assert result.id == message.id


@pytest.mark.asyncio
async def test_messaging_service_continues_if_ws_fails(mock_http_client):
    """If WS gateway is down, message is still created successfully."""
    mock_conv_repo = AsyncMock(spec=ConversationRepository)
    mock_msg_repo = AsyncMock(spec=MessageRepository)
    mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

    sender_id = uuid4()
    recipient_id = uuid4()
    conv_id = uuid4()

    conversation = Conversation(
        id=conv_id,
        participant_1=min(sender_id, recipient_id),
        participant_2=max(sender_id, recipient_id),
        created_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )
    message = Message(
        id=uuid4(),
        conversation_id=conv_id,
        sender_id=sender_id,
        content="Hello!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_conv_repo.get_or_create.return_value = conversation
    mock_msg_repo.create_message.return_value = message

    ws_publisher = WsPublisher(
        http_client=mock_http_client,
        ws_gateway_url="http://localhost:8011",
    )
    service = MessagingService(
        conversation_repo=mock_conv_repo,
        message_repo=mock_msg_repo,
        ws_publisher=ws_publisher,
    )

    result = await service.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="Hello!",
    )

    assert result.id == message.id
    mock_msg_repo.create_message.assert_called_once()
