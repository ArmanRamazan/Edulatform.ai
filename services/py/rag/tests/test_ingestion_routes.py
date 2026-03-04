from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import register_error_handlers, NotFoundError
from app.domain.document import Document
from app.routes.ingestion_routes import create_ingestion_router


def _make_document(doc_id=None, org_id=None):
    return Document(
        id=doc_id or uuid4(),
        organization_id=org_id or uuid4(),
        source_type="text",
        source_path="/doc.md",
        title="Test Doc",
        content="Hello world.",
        metadata={},
        created_at=datetime.now(timezone.utc),
    )


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token
    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


@pytest.fixture
def ingestion_service():
    return AsyncMock()


@pytest.fixture
def client(ingestion_service):
    app = FastAPI()
    register_error_handlers(app)
    router = create_ingestion_router(
        get_service=lambda: ingestion_service,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestPostDocuments:
    def test_creates_document(self, client, ingestion_service):
        doc = _make_document()
        ingestion_service.ingest.return_value = doc
        token = _make_token(role="admin")

        resp = client.post(
            "/documents",
            json={
                "org_id": str(doc.organization_id),
                "source_type": "text",
                "source_path": "/doc.md",
                "title": "Test Doc",
                "content": "Hello world.",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == str(doc.id)
        assert data["title"] == "Test Doc"

    def test_teacher_can_create(self, client, ingestion_service):
        doc = _make_document()
        ingestion_service.ingest.return_value = doc
        token = _make_token(role="teacher", is_verified=True)

        resp = client.post(
            "/documents",
            json={
                "org_id": str(doc.organization_id),
                "source_type": "text",
                "source_path": "/doc.md",
                "title": "T",
                "content": "C",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

    def test_student_forbidden(self, client):
        token = _make_token(role="student")

        resp = client.post(
            "/documents",
            json={
                "org_id": str(uuid4()),
                "source_type": "text",
                "source_path": "/doc.md",
                "title": "T",
                "content": "C",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_no_auth_returns_401(self, client):
        resp = client.post(
            "/documents",
            json={
                "org_id": str(uuid4()),
                "source_type": "text",
                "source_path": "/doc.md",
                "title": "T",
                "content": "C",
            },
        )
        assert resp.status_code == 422 or resp.status_code == 401


class TestGetDocuments:
    def test_returns_list(self, client, ingestion_service):
        docs = [_make_document(), _make_document()]
        ingestion_service.get_documents_by_org.return_value = docs
        token = _make_token(role="admin")
        org_id = uuid4()

        resp = client.get(
            f"/documents?org_id={org_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_no_auth_fails(self, client):
        resp = client.get(f"/documents?org_id={uuid4()}")
        assert resp.status_code in (401, 422)


class TestDeleteDocument:
    def test_deletes_document(self, client, ingestion_service):
        doc_id = uuid4()
        ingestion_service.delete.return_value = True
        token = _make_token(role="admin")

        resp = client.delete(
            f"/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client, ingestion_service):
        ingestion_service.delete.return_value = False
        token = _make_token(role="admin")

        resp = client.delete(
            f"/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_non_admin_forbidden(self, client):
        token = _make_token(role="teacher")

        resp = client.delete(
            f"/documents/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
