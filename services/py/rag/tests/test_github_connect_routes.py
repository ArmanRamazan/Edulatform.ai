from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from common.errors import register_error_handlers
from app.domain.github_repo import OrgGithubRepo
from app.routes.github_connect_routes import create_github_connect_router


def _make_token(user_id=None, role="admin", is_verified=True):
    from common.security import create_access_token

    return create_access_token(
        user_id=str(user_id or uuid4()),
        secret="test-secret",
        extra_claims={"role": role, "is_verified": is_verified},
    )


def _make_repo(org_id=None, repo_url="https://github.com/owner/repo") -> OrgGithubRepo:
    return OrgGithubRepo(
        id=uuid4(),
        organization_id=org_id or uuid4(),
        repo_url=repo_url,
        branch="main",
        last_synced_at=None,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def connect_service():
    return AsyncMock()


@pytest.fixture
def client(connect_service):
    app = FastAPI()
    register_error_handlers(app)
    router = create_github_connect_router(
        get_connect_service=lambda: connect_service,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
    )
    app.include_router(router)
    return TestClient(app)


class TestPostGithubConnect:
    def test_admin_can_connect_repo(self, client, connect_service):
        org_id = uuid4()
        repo_entity = _make_repo(org_id=org_id)
        connect_service.connect.return_value = (repo_entity, 5)
        token = _make_token(role="admin")

        resp = client.post(
            "/github/connect",
            json={
                "org_id": str(org_id),
                "repo_url": "https://github.com/owner/repo",
                "branch": "main",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["ingested_count"] == 5
        assert data["repo_url"] == "https://github.com/owner/repo"

    def test_connect_default_branch_is_main(self, client, connect_service):
        connect_service.connect.return_value = (_make_repo(), 0)
        token = _make_token(role="admin")

        resp = client.post(
            "/github/connect",
            json={
                "org_id": str(uuid4()),
                "repo_url": "https://github.com/o/r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        call_kwargs = connect_service.connect.call_args.kwargs
        assert call_kwargs["branch"] == "main"

    def test_non_admin_role_forbidden(self, client):
        token = _make_token(role="student")

        resp = client.post(
            "/github/connect",
            json={
                "org_id": str(uuid4()),
                "repo_url": "https://github.com/o/r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    def test_teacher_role_forbidden(self, client):
        token = _make_token(role="teacher")

        resp = client.post(
            "/github/connect",
            json={
                "org_id": str(uuid4()),
                "repo_url": "https://github.com/o/r",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    def test_no_auth_returns_401_or_422(self, client):
        resp = client.post(
            "/github/connect",
            json={"org_id": str(uuid4()), "repo_url": "https://github.com/o/r"},
        )

        assert resp.status_code in (401, 422)

    def test_missing_repo_url_returns_422(self, client):
        token = _make_token(role="admin")

        resp = client.post(
            "/github/connect",
            json={"org_id": str(uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 422

    def test_connect_passes_correct_args_to_service(self, client, connect_service):
        org_id = uuid4()
        connect_service.connect.return_value = (_make_repo(org_id=org_id), 3)
        token = _make_token(role="admin")

        resp = client.post(
            "/github/connect",
            json={
                "org_id": str(org_id),
                "repo_url": "https://github.com/myorg/myrepo",
                "branch": "develop",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        call_kwargs = connect_service.connect.call_args.kwargs
        assert call_kwargs["org_id"] == org_id
        assert call_kwargs["repo_url"] == "https://github.com/myorg/myrepo"
        assert call_kwargs["branch"] == "develop"

    def test_response_includes_repo_fields(self, client, connect_service):
        org_id = uuid4()
        repo_entity = _make_repo(org_id=org_id, repo_url="https://github.com/o/r")
        connect_service.connect.return_value = (repo_entity, 7)
        token = _make_token(role="admin")

        resp = client.post(
            "/github/connect",
            json={"org_id": str(org_id), "repo_url": "https://github.com/o/r"},
            headers={"Authorization": f"Bearer {token}"},
        )

        data = resp.json()
        assert "id" in data
        assert "organization_id" in data
        assert data["branch"] == "main"
        assert data["ingested_count"] == 7


class TestPostGithubWebhook:
    def test_push_event_is_processed(self, client, connect_service):
        connect_service.process_webhook.return_value = 3

        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [{"added": ["README.md"], "modified": [], "removed": []}],
        }

        resp = client.post(
            "/github/webhook",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["processed_files"] == 3

    def test_non_push_event_returns_zero_without_processing(
        self, client, connect_service
    ):
        resp = client.post(
            "/github/webhook",
            json={"action": "created"},
            headers={"X-GitHub-Event": "ping"},
        )

        assert resp.status_code == 200
        assert resp.json()["processed_files"] == 0
        connect_service.process_webhook.assert_not_called()

    def test_missing_event_header_returns_zero(self, client, connect_service):
        resp = client.post(
            "/github/webhook",
            json={"ref": "refs/heads/main", "repository": {"full_name": "o/r"}},
        )

        assert resp.status_code == 200
        assert resp.json()["processed_files"] == 0
        connect_service.process_webhook.assert_not_called()

    def test_webhook_requires_no_auth(self, client, connect_service):
        """Webhook endpoint is public (called by GitHub servers)."""
        connect_service.process_webhook.return_value = 1

        resp = client.post(
            "/github/webhook",
            json={
                "ref": "refs/heads/main",
                "repository": {"full_name": "o/r"},
                "commits": [{"added": ["README.md"], "modified": [], "removed": []}],
            },
            headers={"X-GitHub-Event": "push"},
        )

        assert resp.status_code == 200

    def test_webhook_passes_full_payload_to_service(self, client, connect_service):
        connect_service.process_webhook.return_value = 2
        payload = {
            "ref": "refs/heads/main",
            "repository": {"full_name": "owner/repo"},
            "commits": [{"added": ["a.md"], "modified": ["b.py"], "removed": []}],
        }

        client.post(
            "/github/webhook",
            json=payload,
            headers={"X-GitHub-Event": "push"},
        )

        called_payload = connect_service.process_webhook.call_args.kwargs["payload"]
        assert called_payload["repository"]["full_name"] == "owner/repo"
