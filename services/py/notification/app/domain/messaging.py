from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Conversation:
    id: UUID
    participant_1: UUID
    participant_2: UUID
    created_at: datetime
    last_message_at: datetime


@dataclass(frozen=True)
class Message:
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    is_read: bool
    created_at: datetime


@dataclass(frozen=True)
class ConversationPreview:
    conversation_id: UUID
    other_user_id: UUID
    last_message_content: str
    last_message_at: datetime
    unread_count: int


class SendMessageRequest(BaseModel):
    recipient_id: UUID
    content: str


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID
    content: str
    is_read: bool
    created_at: datetime


class ConversationPreviewResponse(BaseModel):
    conversation_id: UUID
    other_user_id: UUID
    last_message_content: str
    last_message_at: datetime
    unread_count: int


class ConversationListResponse(BaseModel):
    items: list[ConversationPreviewResponse]
    total: int


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
