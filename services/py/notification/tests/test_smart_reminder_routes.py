import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.routes.notifications import router
from app.services.smart_reminder_service import SmartReminderService


@pytest.fixture
def mock_smart_service():
    return AsyncMock(spec=SmartReminderService)


@pytest.fixture
def test_app(mock_smart_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._smart_reminder_service = mock_smart_service

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
async def test_smart_reminders_success(client, mock_smart_service, admin_token):
    mock_smart_service.send_smart_reminders.return_value = {
        "users_checked": 10,
        "reminders_sent": 3,
        "skipped_active_streak": 4,
        "skipped_low_cards": 2,
        "skipped_existing": 1,
        "skipped_errors": 0,
    }

    resp = await client.post(
        "/notifications/flashcard-reminders/smart",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["users_checked"] == 10
    assert data["reminders_sent"] == 3
    assert data["skipped_active_streak"] == 4
    assert data["skipped_low_cards"] == 2


@pytest.mark.asyncio
async def test_smart_reminders_forbidden_for_student(client, student_token):
    resp = await client.post(
        "/notifications/flashcard-reminders/smart",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_smart_reminders_no_auth(client):
    resp = await client.post(
        "/notifications/flashcard-reminders/smart",
    )

    assert resp.status_code == 422
