from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError
from common.security import create_access_token
from app.domain.trust_level import LEVEL_NAMES, LEVEL_THRESHOLDS, TrustLevel
from app.routes.trust_levels import router
from app.services.trust_level_service import TrustLevelService


@pytest.fixture
def mock_trust_service():
    return AsyncMock(spec=TrustLevelService)


@pytest.fixture
def test_app(mock_trust_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._trust_level_service = mock_trust_service

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
def admin_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "admin", "is_verified": True},
    )


def _make_trust_level(user_id, org_id, level=0, missions=0, concepts=0) -> TrustLevel:
    return TrustLevel(
        id=uuid4(),
        user_id=user_id if not isinstance(user_id, str) else uuid4(),
        organization_id=org_id,
        level=level,
        total_missions_completed=missions,
        total_concepts_mastered=concepts,
        unlocked_areas=[],
        level_up_at=None,
        created_at=datetime.now(timezone.utc),
    )


class TestGetMyTrustLevel:
    async def test_returns_200_with_trust_level(
        self, client, mock_trust_service, student_token,
    ):
        org_id = uuid4()
        tl = _make_trust_level(uuid4(), org_id, level=2, missions=20, concepts=10)
        mock_trust_service.get_my_level.return_value = tl

        resp = await client.get(
            f"/trust-level/me?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["level"] == 2
        assert body["level_name"] == "Contributor"
        assert body["total_missions_completed"] == 20
        assert body["total_concepts_mastered"] == 10

    async def test_includes_next_level_progress(
        self, client, mock_trust_service, student_token,
    ):
        org_id = uuid4()
        tl = _make_trust_level(uuid4(), org_id, level=1, missions=10, concepts=5)
        mock_trust_service.get_my_level.return_value = tl

        resp = await client.get(
            f"/trust-level/me?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "next_level" in body
        assert body["next_level"]["level"] == 2
        assert body["next_level"]["missions_required"] == 15
        assert body["next_level"]["concepts_required"] == 8

    async def test_max_level_has_no_next(
        self, client, mock_trust_service, student_token,
    ):
        org_id = uuid4()
        tl = _make_trust_level(uuid4(), org_id, level=5, missions=100, concepts=50)
        mock_trust_service.get_my_level.return_value = tl

        resp = await client.get(
            f"/trust-level/me?org_id={org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["next_level"] is None

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get(f"/trust-level/me?org_id={uuid4()}")
        assert resp.status_code in (401, 422)


class TestGetOrgTrustLevels:
    async def test_admin_gets_org_levels(
        self, client, mock_trust_service, admin_token,
    ):
        org_id = uuid4()
        tl1 = _make_trust_level(uuid4(), org_id, level=1, missions=5, concepts=3)
        tl2 = _make_trust_level(uuid4(), org_id, level=3, missions=35, concepts=18)
        mock_trust_service.get_org_levels.return_value = [tl1, tl2]

        resp = await client.get(
            f"/trust-level/org/{org_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["levels"]) == 2

    async def test_non_admin_gets_403(
        self, client, mock_trust_service, student_token,
    ):
        org_id = uuid4()

        resp = await client.get(
            f"/trust-level/org/{org_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )

        assert resp.status_code == 403

    async def test_unauthenticated_returns_error(self, client):
        resp = await client.get(f"/trust-level/org/{uuid4()}")
        assert resp.status_code in (401, 422)
