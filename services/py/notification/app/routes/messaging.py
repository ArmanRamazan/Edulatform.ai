from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query, Response

from common.errors import AppError
from app.domain.messaging import (
    SendMessageRequest,
    MessageResponse,
    MessageListResponse,
    ConversationPreviewResponse,
    ConversationListResponse,
)
from app.services.messaging_service import MessagingService

router = APIRouter(tags=["messaging"])


def _get_messaging_service() -> MessagingService:
    from app.main import get_messaging_service
    return get_messaging_service()


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


def _to_message_response(m: "Message") -> MessageResponse:
    from app.domain.messaging import Message
    return MessageResponse(
        id=m.id,
        conversation_id=m.conversation_id,
        sender_id=m.sender_id,
        content=m.content,
        is_read=m.is_read,
        created_at=m.created_at,
    )


def _to_preview_response(p: "ConversationPreview") -> ConversationPreviewResponse:
    from app.domain.messaging import ConversationPreview
    return ConversationPreviewResponse(
        conversation_id=p.conversation_id,
        other_user_id=p.other_user_id,
        last_message_content=p.last_message_content,
        last_message_at=p.last_message_at,
        unread_count=p.unread_count,
    )


@router.post("/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    body: SendMessageRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MessagingService, Depends(_get_messaging_service)],
) -> MessageResponse:
    message = await service.send_message(
        sender_id=claims["user_id"],
        recipient_id=body.recipient_id,
        content=body.content,
    )
    return _to_message_response(message)


@router.get("/conversations/me", response_model=ConversationListResponse)
async def get_my_conversations(
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MessagingService, Depends(_get_messaging_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationListResponse:
    items, total = await service.get_conversations(claims["user_id"], limit, offset)
    return ConversationListResponse(
        items=[_to_preview_response(p) for p in items],
        total=total,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def get_conversation_messages(
    conversation_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MessagingService, Depends(_get_messaging_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageListResponse:
    items, total = await service.get_messages(
        user_id=claims["user_id"],
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
    )
    return MessageListResponse(
        items=[_to_message_response(m) for m in items],
        total=total,
    )


@router.patch("/messages/{message_id}/read", status_code=204)
async def mark_message_read(
    message_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[MessagingService, Depends(_get_messaging_service)],
) -> Response:
    await service.mark_read(user_id=claims["user_id"], message_id=message_id)
    return Response(status_code=204)
