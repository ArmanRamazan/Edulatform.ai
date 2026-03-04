from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Comment:
    id: UUID
    lesson_id: UUID
    course_id: UUID
    user_id: UUID
    content: str
    parent_id: UUID | None
    upvote_count: int
    created_at: datetime
    updated_at: datetime
    is_pinned: bool = False
    is_teacher_answer: bool = False


@dataclass(frozen=True)
class ThreadedComment:
    comment: Comment
    replies: list[Comment]


@dataclass(frozen=True)
class CommentVote:
    comment_id: UUID
    user_id: UUID
    created_at: datetime


class CreateCommentRequest(BaseModel):
    lesson_id: UUID
    course_id: UUID
    content: str = Field(min_length=1, max_length=5000)
    parent_id: UUID | None = None


class UpdateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class ReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: UUID
    lesson_id: UUID
    course_id: UUID
    user_id: UUID
    content: str
    parent_id: UUID | None
    upvote_count: int
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    is_teacher_answer: bool


class CommentListResponse(BaseModel):
    comments: list[CommentResponse]
    total: int


class ThreadedCommentResponse(BaseModel):
    comment: CommentResponse
    replies: list[CommentResponse]


class ThreadedListResponse(BaseModel):
    threads: list[ThreadedCommentResponse]
    total: int


class UpvoteResponse(BaseModel):
    comment_id: UUID
    upvoted: bool
    upvote_count: int
