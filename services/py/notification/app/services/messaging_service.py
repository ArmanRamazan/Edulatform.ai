from __future__ import annotations

from uuid import UUID

import structlog

from common.errors import AppError, ForbiddenError, NotFoundError
from app.adapters.ws_client import WsPublisher
from app.domain.messaging import ConversationPreview, Message
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository

logger = structlog.get_logger()

MAX_CONTENT_LENGTH = 2000


class MessagingService:
    def __init__(
        self,
        conversation_repo: ConversationRepository,
        message_repo: MessageRepository,
        ws_publisher: WsPublisher | None = None,
    ) -> None:
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._ws_publisher = ws_publisher

    async def send_message(
        self, sender_id: UUID, recipient_id: UUID, content: str,
    ) -> Message:
        if sender_id == recipient_id:
            raise AppError("Cannot send message to yourself", status_code=400)
        if not content or len(content) > MAX_CONTENT_LENGTH:
            raise AppError(
                "Message content must be between 1 and 2000 characters",
                status_code=400,
            )

        conversation = await self._conversation_repo.get_or_create(sender_id, recipient_id)
        message = await self._message_repo.create_message(
            conversation.id, sender_id, content,
        )
        logger.info(
            "message_sent",
            sender_id=str(sender_id),
            recipient_id=str(recipient_id),
            conversation_id=str(conversation.id),
        )

        if self._ws_publisher:
            await self._ws_publisher.publish_notification(
                str(recipient_id),
                {
                    "id": str(message.id),
                    "notification_type": "direct_message",
                    "title": "New message",
                    "body": message.content,
                },
            )

        return message

    async def get_conversations(
        self, user_id: UUID, limit: int = 20, offset: int = 0,
    ) -> tuple[list[ConversationPreview], int]:
        return await self._conversation_repo.get_user_conversations(user_id, limit, offset)

    async def get_messages(
        self, user_id: UUID, conversation_id: UUID, limit: int = 50, offset: int = 0,
    ) -> tuple[list[Message], int]:
        conversation = await self._conversation_repo.get_conversation(conversation_id)
        if not conversation:
            raise NotFoundError("Conversation not found")
        if user_id not in (conversation.participant_1, conversation.participant_2):
            raise ForbiddenError("You are not a participant in this conversation")
        return await self._message_repo.get_messages(conversation_id, limit, offset)

    async def mark_read(self, user_id: UUID, message_id: UUID) -> None:
        message = await self._message_repo.get_by_id(message_id)
        if not message:
            raise NotFoundError("Message not found")
        if message.sender_id == user_id:
            raise ForbiddenError("Only the recipient can mark messages as read")
        await self._message_repo.mark_as_read(message_id, user_id)
