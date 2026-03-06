import pytest
from unittest.mock import AsyncMock, patch

import httpx

from app.adapters.ws_client import WsPublisher
from app.config import Settings


@pytest.fixture
def ws_settings():
    return Settings(ws_gateway_url="http://localhost:8011")


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def ws_publisher(mock_http_client, ws_settings):
    return WsPublisher(http_client=mock_http_client, settings=ws_settings)


class TestWsPublisher:
    async def test_publish_to_user_posts_to_gateway(
        self, ws_publisher, mock_http_client
    ):
        mock_http_client.post.return_value = httpx.Response(
            200, json={"status": "sent"}
        )

        user_id = "550e8400-e29b-41d4-a716-446655440000"
        message = {
            "type": "coach_message",
            "session_id": "00000000-0000-0000-0000-000000000001",
            "content": "Hello!",
            "phase": "recap",
        }

        await ws_publisher.publish_to_user(user_id, message)

        mock_http_client.post.assert_called_once_with(
            "http://localhost:8011/publish",
            json={
                "target": f"user:{user_id}",
                "message": message,
            },
            timeout=2.0,
        )

    async def test_publish_gracefully_handles_connection_error(
        self, ws_publisher, mock_http_client
    ):
        mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

        await ws_publisher.publish_to_user(
            "550e8400-e29b-41d4-a716-446655440000",
            {"type": "coach_message", "content": "test"},
        )

        # Should not raise — fire-and-forget

    async def test_publish_gracefully_handles_timeout(
        self, ws_publisher, mock_http_client
    ):
        mock_http_client.post.side_effect = httpx.TimeoutException("Timeout")

        await ws_publisher.publish_to_user(
            "550e8400-e29b-41d4-a716-446655440000",
            {"type": "coach_message", "content": "test"},
        )

        # Should not raise — fire-and-forget

    async def test_publish_gracefully_handles_http_error(
        self, ws_publisher, mock_http_client
    ):
        mock_http_client.post.return_value = httpx.Response(
            500, json={"error": "internal"}
        )

        await ws_publisher.publish_to_user(
            "550e8400-e29b-41d4-a716-446655440000",
            {"type": "coach_message", "content": "test"},
        )

        # Should not raise — fire-and-forget

    async def test_publish_disabled_when_no_gateway_url(self, mock_http_client):
        settings = Settings(ws_gateway_url="")
        publisher = WsPublisher(http_client=mock_http_client, settings=settings)

        await publisher.publish_to_user(
            "550e8400-e29b-41d4-a716-446655440000",
            {"type": "coach_message", "content": "test"},
        )

        mock_http_client.post.assert_not_called()
