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
    WELCOME = "welcome"
    COURSE_COMPLETED = "course_completed"
    REVIEW_RECEIVED = "review_received"
    STREAK_AT_RISK = "streak_at_risk"
    MISSION_COMPLETED = "mission_completed"
    BADGE_EARNED = "badge_earned"
    STREAK_MILESTONE = "streak_milestone"


EMAIL_TRIGGERING_TYPES: frozenset[str] = frozenset({
    NotificationType.WELCOME,
    NotificationType.COURSE_COMPLETED,
    NotificationType.REVIEW_RECEIVED,
    NotificationType.STREAK_AT_RISK,
})

EMAIL_SUBJECTS: dict[str, str] = {
    NotificationType.WELCOME: "Добро пожаловать в EduPlatform!",
    NotificationType.COURSE_COMPLETED: "Поздравляем с завершением курса!",
    NotificationType.REVIEW_RECEIVED: "Новый отзыв на ваш курс",
    NotificationType.STREAK_AT_RISK: "Ваша серия под угрозой!",
}


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
    email_sent: bool = False
    organization_id: UUID | None = None
    event_id: str | None = None


class NotificationCreate(BaseModel):
    type: NotificationType
    title: str
    body: str = ""
    email: str | None = None


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    body: str
    is_read: bool
    created_at: datetime
    email_sent: bool = False
    organization_id: UUID | None = None
    event_id: str | None = None


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
