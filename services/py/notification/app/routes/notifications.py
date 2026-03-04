from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError, ForbiddenError
from app.domain.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationListResponse,
    StreakReminderRequest,
    StreakReminderResponse,
    FlashcardReminderRequest,
    BulkReminderResponse,
    SmartReminderResponse,
)
from app.services.notification_service import NotificationService
from app.services.smart_reminder_service import SmartReminderService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _get_notification_service() -> NotificationService:
    from app.main import get_notification_service
    return get_notification_service()


def _get_smart_reminder_service() -> SmartReminderService:
    from app.main import get_smart_reminder_service
    return get_smart_reminder_service()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


def _to_response(n: "Notification") -> NotificationResponse:
    from app.domain.notification import Notification
    return NotificationResponse(
        id=n.id,
        user_id=n.user_id,
        type=n.type,
        title=n.title,
        body=n.body,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.post("", response_model=NotificationResponse, status_code=201)
async def create_notification(
    body: NotificationCreate,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[NotificationService, Depends(_get_notification_service)],
) -> NotificationResponse:
    notification = await service.create(
        user_id=claims["user_id"],
        type=body.type,
        title=body.title,
        body=body.body,
    )
    return _to_response(notification)


@router.get("/me", response_model=NotificationListResponse)
async def list_my_notifications(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[NotificationService, Depends(_get_notification_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponse:
    items, total = await service.list_my(claims["user_id"], limit, offset)
    return NotificationListResponse(
        items=[_to_response(n) for n in items],
        total=total,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[NotificationService, Depends(_get_notification_service)],
) -> NotificationResponse:
    notification = await service.mark_as_read(notification_id, claims["user_id"])
    return _to_response(notification)


@router.post("/streak-reminders/send", response_model=StreakReminderResponse)
async def send_streak_reminders(
    body: StreakReminderRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[NotificationService, Depends(_get_notification_service)],
) -> StreakReminderResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can send streak reminders")
    sent_count = await service.send_streak_reminders(body.user_ids)
    return StreakReminderResponse(sent_count=sent_count)


@router.post("/flashcard-reminders/send", response_model=BulkReminderResponse)
async def send_flashcard_reminders(
    body: FlashcardReminderRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[NotificationService, Depends(_get_notification_service)],
) -> BulkReminderResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can send flashcard reminders")
    sent_count = await service.send_flashcard_reminders(
        [{"user_id": item.user_id, "card_count": item.card_count} for item in body.items]
    )
    return BulkReminderResponse(sent_count=sent_count)


@router.post("/flashcard-reminders/smart", response_model=SmartReminderResponse)
async def send_smart_flashcard_reminders(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[SmartReminderService, Depends(_get_smart_reminder_service)],
) -> SmartReminderResponse:
    if claims["role"] != "admin":
        raise ForbiddenError("Only admins can send smart flashcard reminders")
    result = await service.send_smart_reminders()
    return SmartReminderResponse(**result)
