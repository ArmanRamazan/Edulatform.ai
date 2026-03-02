import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
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
def admin_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "admin", "is_verified": True},
    )


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.mark.asyncio
async def test_send_flashcard_reminders(client, mock_service, admin_token):
    user_ids = [str(uuid4()), str(uuid4())]
    mock_service.send_flashcard_reminders.return_value = 2

    resp = await client.post(
        "/notifications/flashcard-reminders/send",
        json={"items": [
            {"user_id": user_ids[0], "card_count": 5},
            {"user_id": user_ids[1], "card_count": 3},
        ]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["sent_count"] == 2


@pytest.mark.asyncio
async def test_send_flashcard_reminders_empty(client, mock_service, admin_token):
    mock_service.send_flashcard_reminders.return_value = 0

    resp = await client.post(
        "/notifications/flashcard-reminders/send",
        json={"items": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["sent_count"] == 0


@pytest.mark.asyncio
async def test_send_flashcard_reminders_forbidden_for_student(client, student_token):
    resp = await client.post(
        "/notifications/flashcard-reminders/send",
        json={"items": [{"user_id": str(uuid4()), "card_count": 5}]},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_send_flashcard_reminders_no_auth(client):
    resp = await client.post(
        "/notifications/flashcard-reminders/send",
        json={"items": [{"user_id": str(uuid4()), "card_count": 5}]},
    )

    assert resp.status_code == 422
