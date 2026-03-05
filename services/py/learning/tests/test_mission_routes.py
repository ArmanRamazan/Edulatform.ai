from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, NotFoundError, ForbiddenError, AppError
from common.security import create_access_token
from app.domain.mission import Mission
from app.routes.missions import router
from app.services.mission_service import MissionService


@pytest.fixture
def mock_mission_service():
    return AsyncMock(spec=MissionService)


@pytest.fixture
def test_app(mock_mission_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._mission_service = mock_mission_service

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


def _make_mission(
    user_id=None,
    org_id=None,
    status: str = "pending",
    score: float | None = None,
    mastery_delta: float | None = None,
) -> Mission:
    return Mission(
        id=uuid4(),
        user_id=user_id or uuid4(),
        organization_id=org_id or uuid4(),
        concept_id=None,
        mission_type="daily",
        status=status,
        blueprint={"topic": "variables"},
        score=score,
        mastery_delta=mastery_delta,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


class TestGetTodayMission:
    async def test_returns_200_with_mission(
        self, client, mock_mission_service, student_token,
    ):
        org_id = uuid4()
        mission = _make_mission(org_id=org_id)
        mock_mission_service.get_or_create_today.return_value = mission

        resp = await client.get(
            f"/missions/today?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert body["mission_type"] == "daily"
        assert "blueprint" in body

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get(f"/missions/today?org_id={uuid4()}")
        assert resp.status_code in (401, 422)


class TestStartMission:
    async def test_returns_200_when_started(
        self, client, mock_mission_service, student_token,
    ):
        mission = _make_mission(status="in_progress")
        mock_mission_service.start_mission.return_value = mission

        resp = await client.post(
            f"/missions/{mission.id}/start",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    async def test_not_found_returns_404(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.start_mission.side_effect = NotFoundError("Mission not found")

        resp = await client.post(
            f"/missions/{uuid4()}/start",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 404

    async def test_wrong_user_returns_403(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.start_mission.side_effect = ForbiddenError()

        resp = await client.post(
            f"/missions/{uuid4()}/start",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 403


class TestCompleteMission:
    async def test_returns_200_with_score(
        self, client, mock_mission_service, student_token,
    ):
        mission = _make_mission(status="completed", score=0.85, mastery_delta=0.1)
        mock_mission_service.complete_mission.return_value = mission

        resp = await client.post(
            f"/missions/{mission.id}/complete",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"session_id": "sess-123"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["score"] == 0.85
        assert body["mastery_delta"] == 0.1

    async def test_not_found_returns_404(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.complete_mission.side_effect = NotFoundError()

        resp = await client.post(
            f"/missions/{uuid4()}/complete",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"session_id": "sess"},
        )

        assert resp.status_code == 404

    async def test_not_in_progress_returns_400(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.complete_mission.side_effect = AppError(
            "Mission is not in progress",
        )

        resp = await client.post(
            f"/missions/{uuid4()}/complete",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"session_id": "sess"},
        )

        assert resp.status_code == 400


class TestGetMyMissions:
    async def test_returns_200_with_list(
        self, client, mock_mission_service, student_token,
    ):
        missions = [_make_mission() for _ in range(3)]
        mock_mission_service.get_my_missions.return_value = missions

        resp = await client.get(
            "/missions/me",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["missions"]) == 3

    async def test_respects_limit_and_offset(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.get_my_missions.return_value = []

        resp = await client.get(
            "/missions/me?limit=5&offset=10",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        mock_mission_service.get_my_missions.assert_awaited_once()


class TestGetStreak:
    async def test_returns_200_with_streak(
        self, client, mock_mission_service, student_token,
    ):
        mock_mission_service.get_streak.return_value = 7

        resp = await client.get(
            "/missions/streak",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["current_streak"] == 7

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get("/missions/streak")
        assert resp.status_code in (401, 422)
