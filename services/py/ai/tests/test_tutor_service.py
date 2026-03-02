from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from common.errors import AppError
from app.config import Settings
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.services.tutor_service import TutorService


@pytest.fixture
def tutor_settings():
    return Settings(tutor_daily_limit=3)


@pytest.fixture
def tutor_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def tutor_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def tutor_service(tutor_llm, tutor_cache, tutor_settings):
    return TutorService(llm=tutor_llm, cache=tutor_cache, settings=tutor_settings)


class TestChat:
    async def test_new_session_creates_session_id(
        self, tutor_service, tutor_llm, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = []
        tutor_llm.generate.return_value = (
            "What do you think Python is best known for?",
            50,
            30,
        )

        result = await tutor_service.chat(
            user_id="user-1",
            lesson_id=str(uuid4()),
            message="What is Python?",
            lesson_content="Python is a high-level language.",
            credits_remaining=9,
        )

        assert result.session_id is not None
        assert len(result.session_id) == 36  # UUID format
        assert result.message == "What do you think Python is best known for?"
        assert result.model_used == "gemini-2.0-flash-lite"
        assert result.credits_remaining == 9

    async def test_existing_session_preserves_id(
        self, tutor_service, tutor_llm, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! What do you know about Python?"},
        ]
        tutor_llm.generate.return_value = ("Good question! Think about it.", 80, 20)

        result = await tutor_service.chat(
            user_id="user-1",
            lesson_id=str(uuid4()),
            message="It's a language right?",
            lesson_content="Python is a high-level language.",
            session_id="existing-session-id",
            credits_remaining=5,
        )

        assert result.session_id == "existing-session-id"
        tutor_cache.get_conversation.assert_called_once_with("existing-session-id")

    async def test_saves_conversation_history(
        self, tutor_service, tutor_llm, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = []
        tutor_llm.generate.return_value = ("What do you think?", 50, 20)

        await tutor_service.chat(
            user_id="user-1",
            lesson_id=str(uuid4()),
            message="Tell me about Python",
            lesson_content="Python is a language.",
            credits_remaining=9,
        )

        tutor_cache.save_conversation.assert_called_once()
        args = tutor_cache.save_conversation.call_args
        messages = args[0][1]
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "Tell me about Python"}
        assert messages[1] == {"role": "assistant", "content": "What do you think?"}

    async def test_includes_history_in_prompt(
        self, tutor_service, tutor_llm, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        tutor_llm.generate.return_value = ("Sure!", 100, 20)

        await tutor_service.chat(
            user_id="user-1",
            lesson_id=str(uuid4()),
            message="Next question",
            lesson_content="Lesson text here.",
            credits_remaining=5,
        )

        prompt = tutor_llm.generate.call_args[0][0]
        assert "Student: Hi" in prompt
        assert "Tutor: Hello!" in prompt
        assert "Student: Next question" in prompt
        assert "LESSON CONTENT:" in prompt

    async def test_credits_remaining_passed_through(
        self, tutor_service, tutor_llm, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = []
        tutor_llm.generate.return_value = ("Answer", 50, 20)

        result = await tutor_service.chat(
            user_id="user-1",
            lesson_id=str(uuid4()),
            message="Hi",
            lesson_content="Content.",
            credits_remaining=42,
        )

        assert result.credits_remaining == 42


class TestFeedback:
    async def test_saves_feedback_successfully(self, tutor_service, tutor_cache):
        tutor_cache.get_conversation.return_value = [
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
        ]

        result = await tutor_service.feedback(
            session_id="sess-1", message_index=1, rating=1
        )

        assert result.status == "ok"
        tutor_cache.save_feedback.assert_called_once_with("sess-1", 1, 1)

    async def test_session_not_found_raises_error(self, tutor_service, tutor_cache):
        tutor_cache.get_conversation.return_value = []

        with pytest.raises(AppError, match="Session not found"):
            await tutor_service.feedback(
                session_id="nonexistent", message_index=0, rating=1
            )

    async def test_invalid_message_index_raises_error(
        self, tutor_service, tutor_cache
    ):
        tutor_cache.get_conversation.return_value = [
            {"role": "user", "content": "Q"},
        ]

        with pytest.raises(AppError, match="Invalid message index"):
            await tutor_service.feedback(
                session_id="sess-1", message_index=5, rating=1
            )
