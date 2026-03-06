from __future__ import annotations

import httpx
import structlog

from app.config import Settings

logger = structlog.get_logger()


class WsPublisher:
    """Fire-and-forget publisher to WebSocket gateway."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self._http_client = http_client
        self._gateway_url = settings.ws_gateway_url

    async def publish_to_user(self, user_id: str, message: dict) -> None:
        if not self._gateway_url:
            return

        try:
            await self._http_client.post(
                f"{self._gateway_url}/publish",
                json={
                    "target": f"user:{user_id}",
                    "message": message,
                },
                timeout=2.0,
            )
        except Exception:
            logger.warning(
                "ws_publish_failed",
                user_id=user_id,
                msg_type=message.get("type"),
                exc_info=True,
            )
