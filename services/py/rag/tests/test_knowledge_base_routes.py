from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import NotFoundError, register_error_handlers
from app.domain.document import Document
from app.domain.search import SearchResult
from app.domain.knowledge_base import KBStats
from app.routes.knowledge_base_routes import create_knowledge_base_router


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token

    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


@pytest.fixture
def kb_service():
    return AsyncMock()


@pytest.fixture
def client(kb_service):
    app = FastAPI()
    register_error_handlers(app)
    router = create_knowledge_base_router(
        get_service=lambda: kb_service,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestGetStats:
    def test_returns_stats(self, client, kb_service):
        org_id = uuid4()
        now = datetime.now(timezone.utc)
        kb_service.get_stats.return_value = KBStats(
            total_documents=5,
            total_chunks=42,
            total_concepts=10,
            last_updated=now,
        )
        token = _make_token(role="admin")

        resp = client.get(
            f"/kb/{org_id}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 5
        assert data["total_chunks"] == 42
        assert data["total_concepts"] == 10
        assert data["last_updated"] is not None

    def test_no_auth_fails(self, client):
        resp = client.get(f"/kb/{uuid4()}/stats")
        assert resp.status_code in (401, 422)

    def test_any_role_can_access(self, client, kb_service):
        kb_service.get_stats.return_value = KBStats(
            total_documents=0, total_chunks=0, total_concepts=0, last_updated=None,
        )
        for role in ("student", "teacher", "admin"):
            token = _make_token(role=role)
            resp = client.get(
                f"/kb/{uuid4()}/stats",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


class TestListSources:
    def test_returns_sources(self, client, kb_service):
        org_id = uuid4()
        now = datetime.now(timezone.utc)
        kb_service.list_sources.return_value = [
            Document(
                id=uuid4(),
                organization_id=org_id,
                source_type="text",
                source_path="/test.md",
                title="Test Doc",
                content="content",
                metadata={},
                created_at=now,
            ),
        ]
        token = _make_token(role="teacher")

        resp = client.get(
            f"/kb/{org_id}/sources",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Doc"
        assert data[0]["source_type"] == "text"

    def test_no_auth_fails(self, client):
        resp = client.get(f"/kb/{uuid4()}/sources")
        assert resp.status_code in (401, 422)


class TestGetConceptGraph:
    def test_returns_graph(self, client, kb_service):
        org_id = uuid4()
        kb_service.get_concept_graph.return_value = {
            "nodes": [{"id": str(uuid4()), "name": "Python", "description": "A language"}],
            "edges": [],
        }
        token = _make_token(role="student")

        resp = client.get(
            f"/kb/{org_id}/concepts",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 1

    def test_no_auth_fails(self, client):
        resp = client.get(f"/kb/{uuid4()}/concepts")
        assert resp.status_code in (401, 422)


class TestSearch:
    def test_returns_results(self, client, kb_service):
        org_id = uuid4()
        kb_service.search.return_value = [
            SearchResult(
                chunk_id=uuid4(),
                content="Some content",
                similarity=0.92,
                document_title="Doc",
                source_type="text",
                source_path="/doc.md",
                metadata={},
            ),
        ]
        token = _make_token(role="student")

        resp = client.post(
            f"/kb/{org_id}/search",
            json={"query": "what is python?", "limit": 3},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["content"] == "Some content"
        assert data[0]["similarity"] == 0.92

    def test_default_limit(self, client, kb_service):
        kb_service.search.return_value = []
        token = _make_token()

        resp = client.post(
            f"/kb/{uuid4()}/search",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        kb_service.search.assert_called_once()
        call_kwargs = kb_service.search.call_args
        assert call_kwargs[1].get("limit", call_kwargs[0][2] if len(call_kwargs[0]) > 2 else 5) == 5

    def test_no_auth_fails(self, client):
        resp = client.post(f"/kb/{uuid4()}/search", json={"query": "test"})
        assert resp.status_code in (401, 422)


class TestRefreshSource:
    def test_admin_can_refresh(self, client, kb_service):
        org_id = uuid4()
        doc_id = uuid4()
        now = datetime.now(timezone.utc)
        kb_service.refresh_source.return_value = Document(
            id=doc_id,
            organization_id=org_id,
            source_type="text",
            source_path="/test.md",
            title="Refreshed",
            content="new content",
            metadata={},
            created_at=now,
        )
        token = _make_token(role="admin")

        resp = client.post(
            f"/kb/{org_id}/refresh/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Refreshed"

    def test_student_forbidden(self, client):
        token = _make_token(role="student")

        resp = client.post(
            f"/kb/{uuid4()}/refresh/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    def test_teacher_forbidden(self, client):
        token = _make_token(role="teacher")

        resp = client.post(
            f"/kb/{uuid4()}/refresh/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    def test_not_found(self, client, kb_service):
        kb_service.refresh_source.side_effect = NotFoundError("Document not found")
        token = _make_token(role="admin")

        resp = client.post(
            f"/kb/{uuid4()}/refresh/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 404

    def test_no_auth_fails(self, client):
        resp = client.post(f"/kb/{uuid4()}/refresh/{uuid4()}")
        assert resp.status_code in (401, 422)
