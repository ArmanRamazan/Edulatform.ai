from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import register_error_handlers
from app.routes.github_routes import create_github_router


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token
    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


@pytest.fixture
def github_adapter():
    return AsyncMock()


@pytest.fixture
def ingestion_service():
    return AsyncMock()


@pytest.fixture
def client(github_adapter, ingestion_service):
    app = FastAPI()
    register_error_handlers(app)
    router = create_github_router(
        get_github_adapter=lambda: github_adapter,
        get_ingestion_service=lambda: ingestion_service,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestPostSourcesGithub:
    def test_indexes_repository(self, client, github_adapter):
        github_adapter.index_repository.return_value = 42
        token = _make_token(role="admin")
        org_id = uuid4()

        resp = client.post(
            "/sources/github",
            json={
                "org_id": str(org_id),
                "owner": "myorg",
                "repo": "myrepo",
                "branch": "main",
                "extensions": [".py", ".md"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["indexed_files_count"] == 42

    def test_default_branch_and_extensions(self, client, github_adapter):
        github_adapter.index_repository.return_value = 5
        token = _make_token(role="admin")

        resp = client.post(
            "/sources/github",
            json={
                "org_id": str(uuid4()),
                "owner": "o",
                "repo": "r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        call_kwargs = github_adapter.index_repository.call_args.kwargs
        assert call_kwargs["branch"] == "main"
        assert call_kwargs["extensions"] == [".py", ".ts", ".md", ".yaml"]

    def test_non_admin_forbidden(self, client):
        token = _make_token(role="student")

        resp = client.post(
            "/sources/github",
            json={
                "org_id": str(uuid4()),
                "owner": "o",
                "repo": "r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_teacher_forbidden(self, client):
        token = _make_token(role="teacher")

        resp = client.post(
            "/sources/github",
            json={
                "org_id": str(uuid4()),
                "owner": "o",
                "repo": "r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_no_auth_fails(self, client):
        resp = client.post(
            "/sources/github",
            json={
                "org_id": str(uuid4()),
                "owner": "o",
                "repo": "r",
            },
        )
        assert resp.status_code in (401, 422)

    def test_missing_required_fields(self, client):
        token = _make_token(role="admin")

        resp = client.post(
            "/sources/github",
            json={"org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
