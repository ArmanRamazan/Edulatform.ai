import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from app.adapters.slack_client import SlackClient, StubSlackClient, WebhookSlackClient


WEBHOOK_URL = "https://hooks.slack.com/services/T00/B00/xxxx"


@pytest.mark.asyncio
async def test_stub_slack_client_returns_true():
    client = StubSlackClient()
    result = await client.send_message(WEBHOOK_URL, "Hello!")
    assert result is True


@pytest.mark.asyncio
async def test_stub_slack_client_is_slack_client():
    client = StubSlackClient()
    assert isinstance(client, SlackClient)


@pytest.mark.asyncio
async def test_webhook_slack_client_sends_post_with_correct_payload():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(return_value=mock_response)

    client = WebhookSlackClient(http_client=mock_http)
    result = await client.send_message(WEBHOOK_URL, "Test message")

    assert result is True
    mock_http.post.assert_called_once_with(
        WEBHOOK_URL,
        json={"text": "Test message"},
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_webhook_slack_client_returns_false_on_http_error():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
    )

    client = WebhookSlackClient(http_client=mock_http)
    result = await client.send_message(WEBHOOK_URL, "Test message")

    assert result is False


@pytest.mark.asyncio
async def test_webhook_slack_client_returns_false_on_network_exception():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(side_effect=Exception("Connection refused"))

    client = WebhookSlackClient(http_client=mock_http)
    result = await client.send_message(WEBHOOK_URL, "Test message")

    assert result is False


@pytest.mark.asyncio
async def test_webhook_slack_client_is_slack_client():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    client = WebhookSlackClient(http_client=mock_http)
    assert isinstance(client, SlackClient)
