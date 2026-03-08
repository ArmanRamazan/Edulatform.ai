import os
import hmac
import hashlib
import time

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.routes.slack import router as slack_router
from app.services.slack_reminder_service import SlackReminderService
from app.services.slack_search_service import SlackSearchService
from app.repositories.slack_config_repo import SlackConfigRepository
from app.domain.slack import SlackConfig


SIGNING_SECRET = "test-signing-secret"
JWT_SECRET = "test-secret"


def _make_slack_signature(body: str, timestamp: str, secret: str) -> str:
    sig_basestring = f"v0:{timestamp}:{body}"
    computed = hmac.new(
        secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return f"v0={computed}"


def _make_config(org_id=None) -> SlackConfig:
    return SlackConfig(
        org_id=org_id or uuid4(),
        webhook_url="https://hooks.slack.com/services/T00/B00/xxxx",
        channel="#engineering",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_reminder_service():
    return AsyncMock(spec=SlackReminderService)


@pytest.fixture
def mock_search_service():
    return AsyncMock(spec=SlackSearchService)


@pytest.fixture
def mock_slack_config_repo():
    return AsyncMock(spec=SlackConfigRepository)


@pytest.fixture
def test_app(mock_reminder_service, mock_search_service, mock_slack_config_repo):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(slack_router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": JWT_SECRET,
        "jwt_algorithm": "HS256",
        "slack_signing_secret": SIGNING_SECRET,
    })()
    main_module._slack_reminder_service = mock_reminder_service
    main_module._slack_search_service = mock_search_service
    main_module._slack_config_repo = mock_slack_config_repo

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def admin_token():
    return create_access_token(
        str(uuid4()), JWT_SECRET,
        extra_claims={"role": "admin", "is_verified": True},
    )


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), JWT_SECRET,
        extra_claims={"role": "student", "is_verified": False},
    )


# ─── Slack command endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_slack_command_without_signature_returns_403(client):
    resp = await client.post(
        "/slack/commands",
        data={"command": "/search", "text": "search foo", "channel_id": "C001",
              "user_id": "U001", "team_id": "T001"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_slack_command_with_invalid_signature_returns_403(client):
    timestamp = str(int(time.time()))
    body = "command=%2Fsearch&text=search+foo&channel_id=C001&user_id=U001&team_id=T001"

    resp = await client.post(
        "/slack/commands",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": "v0=invalidsignature",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_slack_command_search_returns_results(client, mock_search_service):
    mock_search_service.search.return_value = "Results for: foo\n\n1. Foo result - some snippet"

    body = "command=%2Fsearch&text=search+foo&channel_id=C001&user_id=U001&team_id=T001"
    timestamp = str(int(time.time()))
    sig = _make_slack_signature(body, timestamp, SIGNING_SECRET)

    resp = await client.post(
        "/slack/commands",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": sig,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "foo" in data["text"] or "Results" in data["text"]


@pytest.mark.asyncio
async def test_slack_command_unknown_returns_help_text(client):
    body = "command=%2Fsearch&text=unknowncommand&channel_id=C001&user_id=U001&team_id=T001"
    timestamp = str(int(time.time()))
    sig = _make_slack_signature(body, timestamp, SIGNING_SECRET)

    resp = await client.post(
        "/slack/commands",
        content=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Slack-Request-Timestamp": timestamp,
            "X-Slack-Signature": sig,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data


# ─── Reminders endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_reminders_as_admin(client, mock_reminder_service, admin_token):
    mock_reminder_service.send_mission_reminders.return_value = {
        "orgs_checked": 5,
        "reminders_sent": 3,
        "skipped_errors": 0,
    }

    resp = await client.post(
        "/slack/reminders/send",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["orgs_checked"] == 5
    assert data["reminders_sent"] == 3


@pytest.mark.asyncio
async def test_send_reminders_as_non_admin_returns_403(client, student_token):
    resp = await client.post(
        "/slack/reminders/send",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403


# ─── Config endpoints ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_slack_config(client, mock_slack_config_repo, admin_token):
    org_id = uuid4()
    config = _make_config(org_id)
    mock_slack_config_repo.create.return_value = config

    resp = await client.post(
        "/slack/config",
        json={
            "org_id": str(org_id),
            "webhook_url": "https://hooks.slack.com/services/T00/B00/xxxx",
            "channel": "#engineering",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["org_id"] == str(org_id)
    assert "..." in data["webhook_url"]  # webhook is masked


@pytest.mark.asyncio
async def test_get_slack_config(client, mock_slack_config_repo, admin_token):
    org_id = uuid4()
    config = _make_config(org_id)
    mock_slack_config_repo.get_by_org.return_value = config

    resp = await client.get(
        f"/slack/config?org_id={org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["org_id"] == str(org_id)


@pytest.mark.asyncio
async def test_get_slack_config_not_found(client, mock_slack_config_repo, admin_token):
    mock_slack_config_repo.get_by_org.return_value = None

    resp = await client.get(
        f"/slack/config?org_id={uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_slack_config(client, mock_slack_config_repo, admin_token):
    org_id = uuid4()
    mock_slack_config_repo.delete.return_value = True

    resp = await client.post(
        "/slack/config/delete",
        json={"org_id": str(org_id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True


@pytest.mark.asyncio
async def test_post_slack_config_non_admin_returns_403(client, student_token):
    org_id = uuid4()

    resp = await client.post(
        "/slack/config",
        json={
            "org_id": str(org_id),
            "webhook_url": "https://hooks.slack.com/services/T00/B00/xxxx",
            "channel": "#engineering",
        },
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403
