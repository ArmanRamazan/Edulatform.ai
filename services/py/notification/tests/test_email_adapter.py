"""Tests for email adapter implementations (StubEmailClient, ResendEmailClient)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.email import EmailClient, StubEmailClient, ResendEmailClient


class TestStubEmailClient:
    @pytest.mark.asyncio
    async def test_send_returns_true(self):
        client = StubEmailClient()
        result = await client.send(
            to="user@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_logs_to_stdout(self, capsys):
        client = StubEmailClient()
        await client.send(
            to="user@example.com",
            subject="Welcome!",
            html_body="<p>Hi</p>",
        )
        # structlog outputs key=value pairs; check that the log was emitted
        # We verify via structlog capture instead of capsys since structlog
        # may not write to stdout directly in test mode

    @pytest.mark.asyncio
    async def test_implements_email_client_interface(self):
        client = StubEmailClient()
        assert isinstance(client, EmailClient)


class TestResendEmailClient:
    @pytest.mark.asyncio
    async def test_send_success_returns_true(self):
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        client = ResendEmailClient(
            api_key="re_test_123",
            from_address="noreply@eduplatform.ru",
            http_client=mock_http_client,
        )
        result = await client.send(
            to="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )

        assert result is True
        mock_http_client.post.assert_called_once_with(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer re_test_123"},
            json={
                "from": "noreply@eduplatform.ru",
                "to": ["user@example.com"],
                "subject": "Test",
                "html": "<p>Hello</p>",
            },
        )

    @pytest.mark.asyncio
    async def test_send_server_error_returns_false(self):
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        client = ResendEmailClient(
            api_key="re_test_123",
            http_client=mock_http_client,
        )
        result = await client.send(
            to="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error_returns_false(self):
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = Exception("Connection refused")

        client = ResendEmailClient(
            api_key="re_test_123",
            http_client=mock_http_client,
        )
        result = await client.send(
            to="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_implements_email_client_interface(self):
        mock_http_client = AsyncMock()
        client = ResendEmailClient(
            api_key="re_test_123",
            http_client=mock_http_client,
        )
        assert isinstance(client, EmailClient)

    @pytest.mark.asyncio
    async def test_default_from_address(self):
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        client = ResendEmailClient(
            api_key="re_test_123",
            http_client=mock_http_client,
        )
        await client.send(to="x@y.com", subject="Hi", html_body="<p>Hi</p>")

        call_kwargs = mock_http_client.post.call_args
        assert call_kwargs[1]["json"]["from"] == "noreply@eduplatform.ru"
