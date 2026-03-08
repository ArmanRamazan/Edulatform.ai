import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

import httpx

from app.adapters.slack_client import SlackClient
from app.domain.slack import SlackConfig
from app.repositories.slack_config_repo import SlackConfigRepository
from app.services.slack_reminder_service import SlackReminderService


def _make_config(org_id: UUID | None = None) -> SlackConfig:
    return SlackConfig(
        org_id=org_id or uuid4(),
        webhook_url="https://hooks.slack.com/services/T00/B00/xxxx",
        channel="#engineering",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_slack_config_repo():
    return AsyncMock(spec=SlackConfigRepository)


@pytest.fixture
def mock_slack_client():
    return AsyncMock(spec=SlackClient)


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(mock_slack_config_repo, mock_slack_client, mock_http_client):
    return SlackReminderService(
        slack_config_repo=mock_slack_config_repo,
        slack_client=mock_slack_client,
        ai_service_url="http://localhost:8006/api/ai",
        http_client=mock_http_client,
        jwt_secret="test-secret",
    )


@pytest.mark.asyncio
async def test_send_mission_reminders_no_orgs(
    service, mock_slack_config_repo, mock_slack_client
):
    mock_slack_config_repo.list_all.return_value = []

    stats = await service.send_mission_reminders()

    assert stats["orgs_checked"] == 0
    assert stats["reminders_sent"] == 0
    assert stats["skipped_errors"] == 0
    mock_slack_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_mission_reminders_one_org(
    service, mock_slack_config_repo, mock_slack_client, mock_http_client
):
    config = _make_config()
    mock_slack_config_repo.list_all.return_value = [config]
    mock_slack_client.send_message.return_value = True

    mock_response = MagicMock()
    mock_response.json.return_value = {"concept_name": "Distributed Systems"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    stats = await service.send_mission_reminders()

    assert stats["orgs_checked"] == 1
    assert stats["reminders_sent"] == 1
    assert stats["skipped_errors"] == 0
    mock_slack_client.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_mission_reminders_skips_error(
    service, mock_slack_config_repo, mock_slack_client, mock_http_client
):
    config = _make_config()
    mock_slack_config_repo.list_all.return_value = [config]
    mock_http_client.get = AsyncMock(side_effect=Exception("AI service down"))

    stats = await service.send_mission_reminders()

    assert stats["orgs_checked"] == 1
    assert stats["reminders_sent"] == 0
    assert stats["skipped_errors"] == 1


@pytest.mark.asyncio
async def test_message_format_contains_concept_name(
    service, mock_slack_config_repo, mock_slack_client, mock_http_client
):
    config = _make_config()
    mock_slack_config_repo.list_all.return_value = [config]
    mock_slack_client.send_message.return_value = True

    mock_response = MagicMock()
    mock_response.json.return_value = {"concept_name": "CAP Theorem"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    await service.send_mission_reminders()

    call_args = mock_slack_client.send_message.call_args
    text = call_args[0][1]
    assert "CAP Theorem" in text


@pytest.mark.asyncio
async def test_get_daily_concept_returns_concept_name(
    service, mock_http_client
):
    org_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {"concept_name": "Event Sourcing"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    concept_name = await service._get_daily_concept(org_id)

    assert concept_name == "Event Sourcing"
    mock_http_client.get.assert_called_once()
    call_kwargs = mock_http_client.get.call_args[1]
    assert call_kwargs["params"]["org_id"] == str(org_id)


@pytest.mark.asyncio
async def test_get_daily_concept_fallback_when_missing(
    service, mock_http_client
):
    org_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    concept_name = await service._get_daily_concept(org_id)

    assert concept_name == "Dark Knowledge"


@pytest.mark.asyncio
async def test_send_mission_reminders_multiple_orgs(
    service, mock_slack_config_repo, mock_slack_client, mock_http_client
):
    configs = [_make_config() for _ in range(3)]
    mock_slack_config_repo.list_all.return_value = configs
    mock_slack_client.send_message.return_value = True

    mock_response = MagicMock()
    mock_response.json.return_value = {"concept_name": "CQRS"}
    mock_response.raise_for_status = MagicMock()
    mock_http_client.get = AsyncMock(return_value=mock_response)

    stats = await service.send_mission_reminders()

    assert stats["orgs_checked"] == 3
    assert stats["reminders_sent"] == 3
