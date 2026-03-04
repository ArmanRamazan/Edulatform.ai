"""Route-level tests for email notification feature."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.domain.notification import Notification, NotificationType
from app.routes.notifications import router
from app.services.notification_service import NotificationService


@pytest.fixture
def mock_service():
    return AsyncMock(spec=NotificationService)


@pytest.fixture
def test_app(mock_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._notification_service = mock_service
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
def user_token(user_id):
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.mark.asyncio
async def test_create_notification_with_email(client, mock_service, user_id, user_token):
    notif = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.WELCOME,
        title="Welcome!",
        body="Hello",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        email_sent=True,
    )
    mock_service.create.return_value = notif

    resp = await client.post("/notifications", json={
        "type": "welcome",
        "title": "Welcome!",
        "body": "Hello",
        "email": "user@example.com",
    }, headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["email_sent"] is True
    mock_service.create.assert_called_once()
    call_kwargs = mock_service.create.call_args
    assert call_kwargs.kwargs.get("email") == "user@example.com" or \
        (len(call_kwargs.args) >= 5 and call_kwargs.args[4] == "user@example.com") or \
        call_kwargs[1].get("email") == "user@example.com"


@pytest.mark.asyncio
async def test_create_notification_without_email_backward_compat(
    client, mock_service, user_id, user_token,
):
    notif = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Enrolled",
        body="OK",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        email_sent=False,
    )
    mock_service.create.return_value = notif

    resp = await client.post("/notifications", json={
        "type": "enrollment",
        "title": "Enrolled",
        "body": "OK",
    }, headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["email_sent"] is False


@pytest.mark.asyncio
async def test_response_includes_email_sent_field(client, mock_service, user_id, user_token):
    notif = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Test",
        body="",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        email_sent=False,
    )
    mock_service.create.return_value = notif

    resp = await client.post("/notifications", json={
        "type": "enrollment",
        "title": "Test",
    }, headers={"Authorization": f"Bearer {user_token}"})

    assert resp.status_code == 201
    assert "email_sent" in resp.json()
