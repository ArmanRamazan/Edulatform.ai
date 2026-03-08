from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
import structlog

logger = structlog.get_logger()


class SlackClient(ABC):
    """Abstract base class for Slack message delivery."""

    @abstractmethod
    async def send_message(self, webhook_url: str, text: str) -> bool:
        """Send a message to Slack. Returns True on success, False on failure."""


class StubSlackClient(SlackClient):
    """Logs messages to stdout. Safe default for development."""

    async def send_message(self, webhook_url: str, text: str) -> bool:
        logger.info(
            "slack_stub_send",
            webhook_url=webhook_url[:20] + "...",
            text=text,
        )
        return True


class WebhookSlackClient(SlackClient):
    """Sends messages to Slack via Incoming Webhook."""

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self._http = http_client

    async def send_message(self, webhook_url: str, text: str) -> bool:
        try:
            response = await self._http.post(
                webhook_url,
                json={"text": text},
                timeout=5.0,
            )
            response.raise_for_status()
            return True
        except Exception:
            logger.exception("slack_webhook_send_failed", webhook_url=webhook_url[:20] + "...")
            return False
