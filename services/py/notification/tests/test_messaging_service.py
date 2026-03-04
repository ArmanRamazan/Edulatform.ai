import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.messaging import Conversation, Message, ConversationPreview
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.services.messaging_service import MessagingService

from common.errors import AppError, ForbiddenError


@pytest.fixture
def sender_id():
    return uuid4()


@pytest.fixture
def recipient_id():
    return uuid4()


@pytest.fixture
def conversation_id():
    return uuid4()


@pytest.fixture
def sample_conversation(conversation_id, sender_id, recipient_id):
    p1, p2 = sorted([sender_id, recipient_id])
    return Conversation(
        id=conversation_id,
        participant_1=p1,
        participant_2=p2,
        created_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_message(conversation_id, sender_id):
    return Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content="Hello, I have a question about the course",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_conversation_repo():
    return AsyncMock(spec=ConversationRepository)


@pytest.fixture
def mock_message_repo():
    return AsyncMock(spec=MessageRepository)


@pytest.fixture
def messaging_service(mock_conversation_repo, mock_message_repo):
    return MessagingService(
        conversation_repo=mock_conversation_repo,
        message_repo=mock_message_repo,
    )


@pytest.mark.asyncio
async def test_send_message_creates_conversation(
    messaging_service,
    mock_conversation_repo,
    mock_message_repo,
    sender_id,
    recipient_id,
    sample_conversation,
    sample_message,
):
    mock_conversation_repo.get_or_create.return_value = sample_conversation
    mock_message_repo.create_message.return_value = sample_message

    result = await messaging_service.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="Hello, I have a question about the course",
    )

    assert result.id == sample_message.id
    assert result.content == "Hello, I have a question about the course"
    mock_conversation_repo.get_or_create.assert_called_once_with(sender_id, recipient_id)
    mock_message_repo.create_message.assert_called_once_with(
        sample_conversation.id, sender_id, "Hello, I have a question about the course",
    )


@pytest.mark.asyncio
async def test_send_message_existing_conversation(
    messaging_service,
    mock_conversation_repo,
    mock_message_repo,
    sender_id,
    recipient_id,
    sample_conversation,
):
    mock_conversation_repo.get_or_create.return_value = sample_conversation
    second_message = Message(
        id=uuid4(),
        conversation_id=sample_conversation.id,
        sender_id=sender_id,
        content="Follow-up question",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_message_repo.create_message.return_value = second_message

    result = await messaging_service.send_message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        content="Follow-up question",
    )

    assert result.content == "Follow-up question"
    mock_conversation_repo.get_or_create.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_self_raises_error(
    messaging_service, sender_id,
):
    with pytest.raises(AppError, match="Cannot send message to yourself"):
        await messaging_service.send_message(
            sender_id=sender_id,
            recipient_id=sender_id,
            content="Hello myself",
        )


@pytest.mark.asyncio
async def test_send_message_empty_content_raises_error(
    messaging_service, sender_id, recipient_id,
):
    with pytest.raises(AppError, match="Message content must be between 1 and 2000 characters"):
        await messaging_service.send_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content="",
        )


@pytest.mark.asyncio
async def test_send_message_too_long_raises_error(
    messaging_service, sender_id, recipient_id,
):
    with pytest.raises(AppError, match="Message content must be between 1 and 2000 characters"):
        await messaging_service.send_message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content="x" * 2001,
        )


@pytest.mark.asyncio
async def test_get_conversations(
    messaging_service,
    mock_conversation_repo,
    sender_id,
    recipient_id,
    conversation_id,
):
    preview = ConversationPreview(
        conversation_id=conversation_id,
        other_user_id=recipient_id,
        last_message_content="Hello!",
        last_message_at=datetime.now(timezone.utc),
        unread_count=1,
    )
    mock_conversation_repo.get_user_conversations.return_value = ([preview], 1)

    items, total = await messaging_service.get_conversations(sender_id, limit=20, offset=0)

    assert total == 1
    assert len(items) == 1
    assert items[0].other_user_id == recipient_id
    mock_conversation_repo.get_user_conversations.assert_called_once_with(sender_id, 20, 0)


@pytest.mark.asyncio
async def test_get_messages_as_participant(
    messaging_service,
    mock_conversation_repo,
    mock_message_repo,
    sender_id,
    sample_conversation,
    sample_message,
    conversation_id,
):
    mock_conversation_repo.get_conversation.return_value = sample_conversation
    mock_message_repo.get_messages.return_value = ([sample_message], 1)

    items, total = await messaging_service.get_messages(
        user_id=sender_id,
        conversation_id=conversation_id,
        limit=50,
        offset=0,
    )

    assert total == 1
    assert items[0].content == sample_message.content


@pytest.mark.asyncio
async def test_get_messages_non_participant_raises_error(
    messaging_service,
    mock_conversation_repo,
    sample_conversation,
    conversation_id,
):
    mock_conversation_repo.get_conversation.return_value = sample_conversation
    outsider_id = uuid4()

    with pytest.raises(ForbiddenError):
        await messaging_service.get_messages(
            user_id=outsider_id,
            conversation_id=conversation_id,
            limit=50,
            offset=0,
        )


@pytest.mark.asyncio
async def test_get_messages_conversation_not_found(
    messaging_service,
    mock_conversation_repo,
    sender_id,
    conversation_id,
):
    mock_conversation_repo.get_conversation.return_value = None

    from common.errors import NotFoundError
    with pytest.raises(NotFoundError):
        await messaging_service.get_messages(
            user_id=sender_id,
            conversation_id=conversation_id,
            limit=50,
            offset=0,
        )


@pytest.mark.asyncio
async def test_mark_read_success(
    messaging_service,
    mock_message_repo,
    recipient_id,
    sender_id,
    conversation_id,
):
    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content="Hello",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_message_repo.get_by_id.return_value = message
    mock_message_repo.mark_as_read.return_value = True

    await messaging_service.mark_read(user_id=recipient_id, message_id=message.id)

    mock_message_repo.mark_as_read.assert_called_once_with(message.id, recipient_id)


@pytest.mark.asyncio
async def test_mark_read_sender_raises_error(
    messaging_service,
    mock_message_repo,
    sender_id,
    conversation_id,
):
    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        sender_id=sender_id,
        content="Hello",
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    mock_message_repo.get_by_id.return_value = message

    with pytest.raises(ForbiddenError, match="Only the recipient can mark messages as read"):
        await messaging_service.mark_read(user_id=sender_id, message_id=message.id)


@pytest.mark.asyncio
async def test_mark_read_message_not_found(
    messaging_service,
    mock_message_repo,
    sender_id,
):
    mock_message_repo.get_by_id.return_value = None

    from common.errors import NotFoundError
    with pytest.raises(NotFoundError):
        await messaging_service.mark_read(user_id=sender_id, message_id=uuid4())
