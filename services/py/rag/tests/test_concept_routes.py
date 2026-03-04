from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import register_error_handlers
from app.routes.concept_routes import create_concept_router


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token
    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


@pytest.fixture
def extraction_service():
    return AsyncMock()


@pytest.fixture
def concept_store():
    return AsyncMock()


@pytest.fixture
def client(extraction_service, concept_store):
    app = FastAPI()
    register_error_handlers(app)
    router = create_concept_router(
        get_extraction_service=lambda: extraction_service,
        get_concept_store=lambda: concept_store,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestGetConcepts:
    def test_returns_concepts(self, client, concept_store):
        org_id = uuid4()
        concept_store.get_org_concepts.return_value = [
            {
                "id": str(uuid4()),
                "organization_id": str(org_id),
                "name": "FastAPI",
                "description": "Web framework",
                "source_document_id": str(uuid4()),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        token = _make_token(role="admin")

        resp = client.get(
            f"/concepts?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "FastAPI"

    def test_returns_empty_list(self, client, concept_store):
        concept_store.get_org_concepts.return_value = []
        token = _make_token(role="student")

        resp = client.get(
            f"/concepts?org_id={uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_no_auth_fails(self, client):
        resp = client.get(f"/concepts?org_id={uuid4()}")
        assert resp.status_code in (401, 422)

    def test_any_role_can_read(self, client, concept_store):
        concept_store.get_org_concepts.return_value = []
        for role in ("student", "teacher", "admin"):
            token = _make_token(role=role)
            resp = client.get(
                f"/concepts?org_id={uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


class TestPostExtract:
    def test_triggers_extraction(self, client, extraction_service):
        doc_id = uuid4()
        extraction_service.extract_and_store.return_value = None
        token = _make_token(role="admin")

        resp = client.post(
            f"/concepts/extract/{doc_id}",
            json={"org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        extraction_service.extract_and_store.assert_called_once()

    def test_teacher_can_trigger(self, client, extraction_service):
        extraction_service.extract_and_store.return_value = None
        token = _make_token(role="teacher", is_verified=True)

        resp = client.post(
            f"/concepts/extract/{uuid4()}",
            json={"org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202

    def test_student_forbidden(self, client):
        token = _make_token(role="student")

        resp = client.post(
            f"/concepts/extract/{uuid4()}",
            json={"org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_no_auth_fails(self, client):
        resp = client.post(
            f"/concepts/extract/{uuid4()}",
            json={"org_id": str(uuid4())},
        )
        assert resp.status_code in (401, 422)
