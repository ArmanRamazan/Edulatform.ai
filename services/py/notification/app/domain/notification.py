from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class NotificationType(StrEnum):
    REGISTRATION = "registration"
    ENROLLMENT = "enrollment"
    PAYMENT = "payment"
    STREAK_REMINDER = "streak_reminder"


class StreakReminderRequest(BaseModel):
    user_ids: list[UUID]


class StreakReminderResponse(BaseModel):
    sent_count: int


@dataclass(frozen=True)
class Notification:
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    body: str
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    type: NotificationType
    title: str
    body: str = ""


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    body: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
