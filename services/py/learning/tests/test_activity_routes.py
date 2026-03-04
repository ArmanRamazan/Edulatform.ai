from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.domain.activity import Activity
from app.routes.activity import router
from app.services.activity_service import ActivityService


@pytest.fixture
def mock_activity_service():
    return AsyncMock(spec=ActivityService)


@pytest.fixture
def test_app(mock_activity_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._activity_service = mock_activity_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def student_id(student_token):
    import jwt
    payload = jwt.decode(student_token, "test-secret", algorithms=["HS256"])
    return payload["sub"]


class TestGetMyActivity:
    async def test_get_my_activity(
        self, client, mock_activity_service, student_token,
    ):
        uid = uuid4()
        mock_activity_service.get_my_activity.return_value = [
            Activity(
                id=uuid4(), user_id=uid,
                activity_type="quiz_completed",
                payload={"score": 0.9},
                created_at=datetime.now(timezone.utc),
            ),
        ]

        resp = await client.get(
            "/activity/me?limit=10&offset=0",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["activities"]) == 1
        assert body["activities"][0]["activity_type"] == "quiz_completed"

    async def test_get_my_activity_unauthenticated(self, client):
        resp = await client.get("/activity/me")
        assert resp.status_code == 422 or resp.status_code == 401


class TestGetSocialFeed:
    async def test_get_social_feed(
        self, client, mock_activity_service, student_token,
    ):
        uid1, uid2 = uuid4(), uuid4()
        mock_activity_service.get_social_feed.return_value = [
            Activity(
                id=uuid4(), user_id=uid1,
                activity_type="badge_earned",
                payload={"badge_type": "streak_7"},
                created_at=datetime.now(timezone.utc),
            ),
        ]

        resp = await client.get(
            f"/activity/feed?user_ids={uid1},{uid2}&limit=10&offset=0",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["activities"]) == 1

    async def test_get_social_feed_unauthenticated(self, client):
        resp = await client.get("/activity/feed?user_ids=abc")
        assert resp.status_code == 422 or resp.status_code == 401
