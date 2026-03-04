from __future__ import annotations

from abc import ABC, abstractmethod

import httpx
import structlog

logger = structlog.get_logger()


class EmailClient(ABC):
    """Abstract base class for email delivery."""

    @abstractmethod
    async def send(self, to: str, subject: str, html_body: str) -> bool:
        """Send an email. Returns True on success, False on failure."""


class StubEmailClient(EmailClient):
    """Logs emails to stdout. Safe default for development."""

    async def send(self, to: str, subject: str, html_body: str) -> bool:
        logger.info(
            "email_stub_send",
            to=to,
            subject=subject,
        )
        return True


class ResendEmailClient(EmailClient):
    """Sends emails via Resend API (https://resend.com)."""

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient,
        from_address: str = "noreply@eduplatform.ru",
    ) -> None:
        self._api_key = api_key
        self._from_address = from_address
        self._http_client = http_client

    async def send(self, to: str, subject: str, html_body: str) -> bool:
        try:
            response = await self._http_client.post(
                self.RESEND_API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._from_address,
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                },
            )
            if response.status_code == 200:
                return True
            logger.error(
                "resend_api_error",
                status_code=response.status_code,
                response_text=response.text,
            )
            return False
        except Exception:
            logger.exception("resend_send_failed", to=to, subject=subject)
            return False


# Backward compatibility alias
EmailAdapter = StubEmailClient
