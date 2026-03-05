from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.domain.daily import DailySummary
from app.domain.mission import Mission
from app.domain.trust_level import TrustLevel
from app.routes.daily_routes import router
from app.services.daily_service import DailyService


@pytest.fixture
def mock_daily_service():
    return AsyncMock(spec=DailyService)


@pytest.fixture
def test_app(mock_daily_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._daily_service = mock_daily_service

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


def _make_summary(
    mission: Mission | None = None,
    streak_days: int = 5,
    due_flashcards: int = 3,
) -> DailySummary:
    user_id = uuid4()
    org_id = uuid4()
    if mission is None:
        mission = Mission(
            id=uuid4(),
            user_id=user_id,
            organization_id=org_id,
            concept_id=uuid4(),
            mission_type="daily",
            status="pending",
            blueprint={"concept_name": "Docker", "questions": []},
            score=None,
            mastery_delta=None,
            started_at=None,
            completed_at=None,
            created_at=datetime.now(timezone.utc),
        )
    trust_level = TrustLevel(
        id=uuid4(),
        user_id=user_id,
        organization_id=org_id,
        level=2,
        total_missions_completed=15,
        total_concepts_mastered=8,
        unlocked_areas=["quizzes"],
        level_up_at=None,
        created_at=datetime.now(timezone.utc),
    )
    return DailySummary(
        mission=mission,
        trust_level=trust_level,
        due_flashcards=due_flashcards,
        streak_days=streak_days,
        greeting=f"Day {streak_days}. Today's topic: Docker.",
    )


class TestGetDailySummary:
    async def test_returns_200_with_summary(
        self, client, mock_daily_service, student_token,
    ):
        org_id = uuid4()
        summary = _make_summary()
        mock_daily_service.get_daily_summary.return_value = summary

        resp = await client.get(
            f"/daily/me?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["due_flashcards"] == 3
        assert body["streak_days"] == 5
        assert "greeting" in body
        assert body["mission"] is not None
        assert body["trust_level"]["level"] == 2

    async def test_returns_null_mission(
        self, client, mock_daily_service, student_token,
    ):
        org_id = uuid4()
        user_id = uuid4()
        trust_level = TrustLevel(
            id=uuid4(),
            user_id=user_id,
            organization_id=org_id,
            level=0,
            total_missions_completed=0,
            total_concepts_mastered=0,
            unlocked_areas=[],
            level_up_at=None,
            created_at=datetime.now(timezone.utc),
        )
        summary = DailySummary(
            mission=None,
            trust_level=trust_level,
            due_flashcards=0,
            streak_days=0,
            greeting="Welcome! Let's get started.",
        )
        mock_daily_service.get_daily_summary.return_value = summary

        resp = await client.get(
            f"/daily/me?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["mission"] is None
        assert body["streak_days"] == 0

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get(f"/daily/me?org_id={uuid4()}")
        assert resp.status_code in (401, 422)
