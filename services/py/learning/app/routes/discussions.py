from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Query

from common.errors import AppError
from app.domain.discussion import (
    CommentListResponse,
    CommentResponse,
    CreateCommentRequest,
    ReplyRequest,
    ThreadedListResponse,
    UpdateCommentRequest,
    UpvoteResponse,
)
from app.services.discussion_service import DiscussionService

router = APIRouter(prefix="/discussions", tags=["discussions"])


def _get_discussion_service() -> DiscussionService:
    from app.main import get_discussion_service
    return get_discussion_service()


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


@router.post("/comments", response_model=CommentResponse, status_code=201)
async def create_comment(
    body: CreateCommentRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> CommentResponse:
    return await service.create_comment(
        lesson_id=body.lesson_id,
        course_id=body.course_id,
        user_id=claims["user_id"],
        content=body.content,
        parent_id=body.parent_id,
    )


@router.get("/lessons/{lesson_id}/comments", response_model=ThreadedListResponse)
async def list_comments(
    lesson_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ThreadedListResponse:
    return await service.list_threaded_comments(lesson_id, limit=limit, offset=offset)


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    body: UpdateCommentRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> CommentResponse:
    return await service.update_comment(
        comment_id=comment_id,
        user_id=claims["user_id"],
        content=body.content,
    )


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> None:
    await service.delete_comment(
        comment_id=comment_id,
        user_id=claims["user_id"],
    )


@router.post("/comments/{comment_id}/upvote", response_model=UpvoteResponse)
async def toggle_upvote(
    comment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> UpvoteResponse:
    return await service.toggle_upvote(
        comment_id=comment_id,
        user_id=claims["user_id"],
    )


@router.post(
    "/comments/{comment_id}/reply",
    response_model=CommentResponse,
    status_code=201,
)
async def create_reply(
    comment_id: UUID,
    body: ReplyRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> CommentResponse:
    return await service.create_reply(
        user_id=claims["user_id"],
        comment_id=comment_id,
        content=body.content,
    )


@router.patch("/comments/{comment_id}/pin", response_model=CommentResponse)
async def pin_comment(
    comment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> CommentResponse:
    return await service.pin_comment(
        user_id=claims["user_id"],
        comment_id=comment_id,
        role=claims["role"],
    )


@router.patch(
    "/comments/{comment_id}/mark-answer", response_model=CommentResponse,
)
async def mark_teacher_answer(
    comment_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[DiscussionService, Depends(_get_discussion_service)],
) -> CommentResponse:
    return await service.mark_teacher_answer(
        user_id=claims["user_id"],
        comment_id=comment_id,
        role=claims["role"],
    )
