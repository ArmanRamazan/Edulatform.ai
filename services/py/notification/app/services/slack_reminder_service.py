from __future__ import annotations

from uuid import UUID

import httpx
import structlog

from common.security import create_access_token
from app.adapters.slack_client import SlackClient
from app.domain.slack import SlackConfig
from app.repositories.slack_config_repo import SlackConfigRepository

logger = structlog.get_logger()


class SlackReminderService:
    def __init__(
        self,
        slack_config_repo: SlackConfigRepository,
        slack_client: SlackClient,
        ai_service_url: str,
        http_client: httpx.AsyncClient,
        jwt_secret: str,
    ) -> None:
        self._slack_config_repo = slack_config_repo
        self._slack_client = slack_client
        self._ai_base_url = ai_service_url.rstrip("/")
        self._http = http_client
        self._jwt_secret = jwt_secret

    async def send_mission_reminders(self) -> dict[str, int]:
        """For each org with slack config, post daily mission reminder."""
        configs = await self._slack_config_repo.list_all()
        stats: dict[str, int] = {
            "orgs_checked": len(configs),
            "reminders_sent": 0,
            "skipped_errors": 0,
        }
        for config in configs:
            try:
                await self._send_org_reminder(config, stats)
            except Exception:
                logger.warning("slack_reminder_org_error", org_id=str(config.org_id), exc_info=True)
                stats["skipped_errors"] += 1
        return stats

    async def _send_org_reminder(self, config: SlackConfig, stats: dict[str, int]) -> None:
        """Fetch daily mission concept from AI service and post to Slack."""
        concept_name = await self._get_daily_concept(config.org_id)
        text = f"Daily Mission Ready: *{concept_name}* — Visit the platform to start your mission!"
        ok = await self._slack_client.send_message(config.webhook_url, text)
        if ok:
            stats["reminders_sent"] += 1

    async def _get_daily_concept(self, org_id: UUID) -> str:
        """GET /missions/daily?org_id=... returns {"concept_name": "..."}"""
        token = self._make_service_token(org_id)
        resp = await self._http.get(
            f"{self._ai_base_url}/missions/daily",
            params={"org_id": str(org_id)},
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("concept_name", "Dark Knowledge")

    def _make_service_token(self, org_id: UUID) -> str:
        return create_access_token(
            str(org_id),
            self._jwt_secret,
            extra_claims={"role": "admin", "is_verified": True},
        )
