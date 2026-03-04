from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import register_error_handlers
from app.domain.search import SearchResult
from app.routes.search_routes import create_search_router


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token
    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


def _make_search_result(chunk_id=None):
    return SearchResult(
        chunk_id=chunk_id or uuid4(),
        content="Some relevant content.",
        similarity=0.92,
        document_title="Test Doc",
        source_type="text",
        source_path="/doc.md",
        metadata={},
    )


@pytest.fixture
def search_service():
    return AsyncMock()


@pytest.fixture
def client(search_service):
    app = FastAPI()
    register_error_handlers(app)
    router = create_search_router(
        get_service=lambda: search_service,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestPostSearch:
    def test_returns_results(self, client, search_service):
        results = [_make_search_result(), _make_search_result()]
        search_service.search.return_value = results
        token = _make_token(role="student")
        org_id = uuid4()

        resp = client.post(
            "/search",
            json={"query": "what is python?", "org_id": str(org_id), "limit": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "what is python?"
        assert len(data["results"]) == 2
        assert data["results"][0]["content"] == "Some relevant content."
        assert data["results"][0]["similarity"] == 0.92

    def test_default_limit(self, client, search_service):
        search_service.search.return_value = []
        token = _make_token()

        resp = client.post(
            "/search",
            json={"query": "test", "org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        call_args = search_service.search.call_args
        assert call_args[1].get("limit", call_args[0][2] if len(call_args[0]) > 2 else 5) == 5

    def test_any_role_can_search(self, client, search_service):
        search_service.search.return_value = []

        for role in ("student", "teacher", "admin"):
            token = _make_token(role=role)
            resp = client.post(
                "/search",
                json={"query": "test", "org_id": str(uuid4())},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200, f"role={role} should be allowed"

    def test_no_auth_fails(self, client):
        resp = client.post(
            "/search",
            json={"query": "test", "org_id": str(uuid4())},
        )
        assert resp.status_code in (401, 422)

    def test_empty_query_fails(self, client, search_service):
        token = _make_token()
        resp = client.post(
            "/search",
            json={"query": "", "org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_result_includes_source_info(self, client, search_service):
        search_service.search.return_value = [_make_search_result()]
        token = _make_token()

        resp = client.post(
            "/search",
            json={"query": "test", "org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        result = resp.json()["results"][0]
        assert "document_title" in result
        assert "source_type" in result
        assert "source_path" in result
        assert "chunk_id" in result
