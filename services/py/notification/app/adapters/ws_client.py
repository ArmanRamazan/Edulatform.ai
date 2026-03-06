from __future__ import annotations

import httpx
import structlog

logger = structlog.get_logger()


class WsPublisher:
    """Fire-and-forget publisher to the WebSocket gateway."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        ws_gateway_url: str,
    ) -> None:
        self._http_client = http_client
        self._publish_url = f"{ws_gateway_url}/publish"

    async def publish_notification(
        self, user_id: str, notification: dict,
    ) -> None:
        """Publish a notification to the WS gateway. Never raises."""
        try:
            await self._http_client.post(
                self._publish_url,
                json={
                    "target": f"user:{user_id}",
                    "message": {
                        "type": "notification",
                        **notification,
                    },
                },
                timeout=5.0,
            )
        except Exception:
            logger.warning(
                "ws_publish_failed",
                user_id=user_id,
            )
