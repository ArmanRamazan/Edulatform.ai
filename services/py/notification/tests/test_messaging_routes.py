import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError, NotFoundError
from common.security import create_access_token
from app.domain.messaging import Conversation, Message, ConversationPreview
from app.routes.messaging import router
from app.services.messaging_service import MessagingService


@pytest.fixture
def mock_messaging_service():
    return AsyncMock(spec=MessagingService)


@pytest.fixture
def test_app(mock_messaging_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._messaging_service = mock_messaging_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def recipient_id():
    return uuid4()


@pytest.fixture
def user_token(user_id):
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.mark.asyncio
async def test_send_message(
    client, mock_messaging_service, user_id, recipient_id, user_token, conversation_id,
):
    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=user_id,
        content="Hello teacher!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_messaging_service.send_message.return_value = message

    resp = await client.post("/messages", json={
        "recipient_id": str(recipient_id),
        "content": "Hello teacher!",
    }, headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello teacher!"
    assert data["sender_id"] == str(user_id)


@pytest.mark.asyncio
async def test_send_message_no_auth(client):
    resp = await client.post("/messages", json={
        "recipient_id": str(uuid4()),
        "content": "Hello",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_conversations(
    client, mock_messaging_service, user_id, recipient_id, user_token, conversation_id,
):
    preview = ConversationPreview(
        conversation_id=conversation_id,
        other_user_id=recipient_id,
        last_message_content="Hello!",
        last_message_at=datetime.now(timezone.utc),
        unread_count=2,
    )
    mock_messaging_service.get_conversations.return_value = ([preview], 1)

    resp = await client.get("/conversations/me",
        headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["unread_count"] == 2


@pytest.mark.asyncio
async def test_get_messages(
    client, mock_messaging_service, user_id, user_token, conversation_id,
):
    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=user_id,
        content="Test message",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_messaging_service.get_messages.return_value = ([message], 1)

    resp = await client.get(f"/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["content"] == "Test message"


@pytest.mark.asyncio
async def test_get_messages_non_participant(
    client, mock_messaging_service, user_token, conversation_id,
):
    mock_messaging_service.get_messages.side_effect = ForbiddenError(
        "You are not a participant in this conversation"
    )

    resp = await client.get(f"/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mark_message_read(
    client, mock_messaging_service, user_token,
):
    message_id = uuid4()
    mock_messaging_service.mark_read.return_value = None

    resp = await client.patch(f"/messages/{message_id}/read",
        headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_mark_message_read_not_recipient(
    client, mock_messaging_service, user_token,
):
    message_id = uuid4()
    mock_messaging_service.mark_read.side_effect = ForbiddenError(
        "Only the recipient can mark messages as read"
    )

    resp = await client.patch(f"/messages/{message_id}/read",
        headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 403
