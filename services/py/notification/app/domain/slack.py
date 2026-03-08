from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class SlackConfig:
    org_id: UUID
    webhook_url: str
    channel: str
    created_at: datetime


class SlackConfigCreate(BaseModel):
    org_id: UUID
    webhook_url: str
    channel: str = "#engineering"


class SlackConfigResponse(BaseModel):
    org_id: UUID
    webhook_url: str
    channel: str
    created_at: datetime

    @classmethod
    def from_entity(cls, config: SlackConfig) -> SlackConfigResponse:
        masked = config.webhook_url[:20] + "..." if len(config.webhook_url) > 20 else config.webhook_url
        return cls(
            org_id=config.org_id,
            webhook_url=masked,
            channel=config.channel,
            created_at=config.created_at,
        )


class SlackCommandResponse(BaseModel):
    response_type: str = "in_channel"
    text: str


class SlackReminderResponse(BaseModel):
    orgs_checked: int
    reminders_sent: int
    skipped_errors: int


class SlackConfigDeleteRequest(BaseModel):
    org_id: UUID


class SlackConfigDeleteResponse(BaseModel):
    deleted: bool
