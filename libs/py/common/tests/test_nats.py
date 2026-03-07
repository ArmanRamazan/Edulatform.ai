"""Tests for the NATS JetStream client wrapper.

TDD Red → Green → Refactor cycle.
Tests describe behaviour, not implementation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.nats import NATSClient, create_nats_client


class TestCreateNatsClient:
    def test_returns_nats_client_instance(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        assert isinstance(client, NATSClient)

    def test_stores_url(self) -> None:
        client = create_nats_client("nats://nats:4222")
        assert client.url == "nats://nats:4222"


def _make_mock_nc(mock_js: MagicMock) -> AsyncMock:
    """Build a mock NATS connection where .jetstream() is synchronous (as in nats-py)."""
    mock_nc = AsyncMock()
    mock_nc.jetstream = MagicMock(return_value=mock_js)
    return mock_nc


class TestNATSClientConnect:
    async def test_connect_calls_nats_connect(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        mock_js = MagicMock()
        mock_nc = _make_mock_nc(mock_js)

        with patch("common.nats.nats.connect", return_value=mock_nc) as mock_connect:
            await client.connect()
            mock_connect.assert_called_once_with(
                "nats://localhost:4222",
                reconnect_time_wait=2,
                max_reconnect_attempts=-1,
            )

    async def test_connect_stores_jetstream_handle(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        mock_js = MagicMock()
        mock_nc = _make_mock_nc(mock_js)

        with patch("common.nats.nats.connect", return_value=mock_nc):
            await client.connect()

        assert client.jetstream is mock_js

    async def test_connect_is_idempotent(self) -> None:
        """Calling connect() twice does not open a second connection."""
        client = create_nats_client("nats://localhost:4222")
        mock_nc = _make_mock_nc(MagicMock())

        with patch("common.nats.nats.connect", return_value=mock_nc) as mock_connect:
            await client.connect()
            await client.connect()
            mock_connect.assert_called_once()


class TestNATSClientPublish:
    async def test_publish_sends_bytes_payload(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        mock_js = AsyncMock()
        mock_nc = _make_mock_nc(mock_js)

        with patch("common.nats.nats.connect", return_value=mock_nc):
            await client.connect()

        payload = b'{"event": "mastery.updated"}'
        await client.publish("platform.mastery.updated", payload)

        mock_js.publish.assert_called_once_with(
            "platform.mastery.updated", payload
        )

    async def test_publish_raises_when_not_connected(self) -> None:
        client = create_nats_client("nats://localhost:4222")

        with pytest.raises(RuntimeError, match="not connected"):
            await client.publish("platform.mastery.updated", b"{}")


class TestNATSClientClose:
    async def test_close_drains_connection(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        mock_nc = _make_mock_nc(MagicMock())

        with patch("common.nats.nats.connect", return_value=mock_nc):
            await client.connect()
            await client.close()

        mock_nc.drain.assert_called_once()

    async def test_close_is_safe_when_not_connected(self) -> None:
        """close() on an unconnected client must not raise."""
        client = create_nats_client("nats://localhost:4222")
        await client.close()  # must not raise

    async def test_close_clears_jetstream_handle(self) -> None:
        client = create_nats_client("nats://localhost:4222")
        mock_nc = _make_mock_nc(MagicMock())

        with patch("common.nats.nats.connect", return_value=mock_nc):
            await client.connect()
            await client.close()

        assert client.jetstream is None
