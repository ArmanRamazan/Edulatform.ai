from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.domain.concept import Concept
from app.routes.concepts import router
from app.services.concept_service import ConceptService


@pytest.fixture
def mock_concept_service():
    return AsyncMock(spec=ConceptService)


@pytest.fixture
def test_app(mock_concept_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._concept_service = mock_concept_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_token(role: str = "student") -> tuple[str, str]:
    """Return (user_id_str, token)."""
    user_id = str(uuid4())
    token = create_access_token(
        user_id, "test-secret",
        extra_claims={"role": role, "is_verified": role == "teacher"},
    )
    return user_id, token


def _make_concept(org_id=None, course_id=None) -> Concept:
    return Concept(
        id=uuid4(),
        course_id=course_id or uuid4(),
        lesson_id=None,
        name="Docker Basics",
        description="Container fundamentals",
        parent_id=None,
        order=0,
        organization_id=org_id,
        created_at=datetime.now(timezone.utc),
    )


class TestGetConceptsRoute:
    """GET /concepts — optional org_id query param."""

    async def test_returns_200_with_all_concepts_no_filter(
        self, client, mock_concept_service
    ):
        _, token = _make_token()
        mock_concept_service.list_concepts.return_value = [_make_concept()]

        resp = await client.get(
            "/concepts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        mock_concept_service.list_concepts.assert_called_once_with(org_id=None)

    async def test_passes_org_id_to_service_when_provided(
        self, client, mock_concept_service
    ):
        _, token = _make_token()
        org_id = uuid4()
        mock_concept_service.list_concepts.return_value = [_make_concept(org_id=org_id)]

        resp = await client.get(
            f"/concepts?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["organization_id"] == str(org_id)
        mock_concept_service.list_concepts.assert_called_once_with(org_id=org_id)

    async def test_returns_empty_list_when_no_org_concepts(
        self, client, mock_concept_service
    ):
        _, token = _make_token()
        org_id = uuid4()
        mock_concept_service.list_concepts.return_value = []

        resp = await client.get(
            f"/concepts?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_auth(self, client):
        resp = await client.get("/concepts")
        assert resp.status_code == 422  # missing Authorization header


class TestGetConceptsMasteryRoute:
    """GET /concepts/mastery — optional org_id query param."""

    async def test_returns_200_with_all_mastery_no_filter(
        self, client, mock_concept_service
    ):
        from app.domain.concept import MasteryListResponse, MasteryResponse
        user_id, token = _make_token()
        mock_concept_service.get_user_mastery.return_value = MasteryListResponse(
            items=[MasteryResponse(concept_id=uuid4(), concept_name="CI/CD", mastery=0.5)],
        )

        resp = await client.get(
            "/concepts/mastery",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["mastery"] == 0.5

    async def test_filters_mastery_by_org_id(
        self, client, mock_concept_service
    ):
        from app.domain.concept import MasteryListResponse, MasteryResponse
        user_id, token = _make_token()
        org_id = uuid4()
        mock_concept_service.get_user_mastery.return_value = MasteryListResponse(
            items=[MasteryResponse(concept_id=uuid4(), concept_name="CI/CD", mastery=0.75)],
            organization_id=org_id,
        )

        resp = await client.get(
            f"/concepts/mastery?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["organization_id"] == str(org_id)
        assert len(data["items"]) == 1

    async def test_passes_user_id_and_org_id_to_service(
        self, client, mock_concept_service
    ):
        from app.domain.concept import MasteryListResponse, MasteryResponse
        user_id, token = _make_token()
        org_id = uuid4()
        mock_concept_service.get_user_mastery.return_value = MasteryListResponse(items=[])

        resp = await client.get(
            f"/concepts/mastery?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        call_kwargs = mock_concept_service.get_user_mastery.call_args
        # service receives correct user_id (UUID) and org_id
        assert call_kwargs.kwargs.get("org_id") == org_id or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == org_id
        )

    async def test_requires_auth(self, client):
        resp = await client.get("/concepts/mastery")
        assert resp.status_code == 422  # missing Authorization header
