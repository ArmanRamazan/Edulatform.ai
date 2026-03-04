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
    FLASHCARD_REMINDER = "flashcard_reminder"


class StreakReminderRequest(BaseModel):
    user_ids: list[UUID]


class FlashcardReminderItem(BaseModel):
    user_id: UUID
    card_count: int


class FlashcardReminderRequest(BaseModel):
    items: list[FlashcardReminderItem]


class StreakReminderResponse(BaseModel):
    sent_count: int


class BulkReminderResponse(BaseModel):
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


class SmartReminderResponse(BaseModel):
    users_checked: int
    reminders_sent: int
    skipped_active_streak: int
    skipped_low_cards: int
    skipped_existing: int
    skipped_errors: int
