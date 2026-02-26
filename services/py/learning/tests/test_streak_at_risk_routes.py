from __future__ import annotations

from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.routes.streaks import router
from app.services.streak_service import StreakService


@pytest.fixture
def mock_streak_service():
    return AsyncMock(spec=StreakService)


@pytest.fixture
def test_app(mock_streak_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._streak_service = mock_streak_service

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
async def test_get_at_risk_users(client, mock_streak_service, admin_token):
    user1, user2 = uuid4(), uuid4()
    mock_streak_service.get_at_risk_user_ids.return_value = [user1, user2]

    resp = await client.get(
        "/streaks/at-risk",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["user_ids"]) == 2


@pytest.mark.asyncio
async def test_get_at_risk_users_empty(client, mock_streak_service, admin_token):
    mock_streak_service.get_at_risk_user_ids.return_value = []

    resp = await client.get(
        "/streaks/at-risk",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["user_ids"] == []


@pytest.mark.asyncio
async def test_get_at_risk_users_forbidden_for_student(client, student_token):
    resp = await client.get(
        "/streaks/at-risk",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403
