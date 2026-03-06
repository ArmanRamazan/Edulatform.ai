"""Tests for Coach + WebSocket gateway integration.

Verifies that:
- Coach publishes typing indicator and response via WsPublisher
- Coach still works if WsPublisher fails (graceful degradation)
- Existing behavior is unchanged
"""
import json
import time
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.config import Settings
from app.domain.coach import CoachMessage
from app.domain.mission import (
    MissionBlueprint,
    RecapQuestion,
    CheckQuestion,
    CodeCase,
)
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.adapters.ws_client import WsPublisher
from app.services.coach_service import CoachService


@pytest.fixture
def ws_settings():
    return Settings(ws_gateway_url="http://localhost:8011")


@pytest.fixture
def coach_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def coach_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def ws_publisher():
    return AsyncMock(spec=WsPublisher)


@pytest.fixture
def coach_service_with_ws(coach_llm, coach_cache, ws_settings, ws_publisher):
    return CoachService(
        llm=coach_llm, cache=coach_cache, settings=ws_settings, ws_publisher=ws_publisher
    )


@pytest.fixture
def sample_mission():
    return MissionBlueprint(
        concept_name="Python Decorators",
        concept_id=uuid4(),
        recap_questions=[
            RecapQuestion(
                question="What is a closure?",
                expected_answer="A function that captures variables from enclosing scope",
                concept_ref="closures",
            ),
        ],
        reading_content="Decorators are functions that modify other functions...",
        check_questions=[
            CheckQuestion(
                question="What does @decorator syntax do?",
                options=["Calls the function", "Wraps the function", "Deletes the function", "Imports the function"],
                correct_index=1,
                explanation="@ syntax applies the decorator to the function below it",
            ),
        ],
        code_case=CodeCase(
            code_snippet="def timer(func): pass",
            language="python",
            question="What happens?",
            expected_answer="Nothing special",
            source_path="examples/decorators.py",
        ),
    )


class TestCoachChatPublishesViaWs:
    async def test_chat_publishes_typing_indicator(
        self, coach_service_with_ws, coach_llm, coach_cache, ws_publisher
    ):
        user_id = uuid4()
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "You are a Coach...",
            "messages": [{"role": "assistant", "content": "What is a closure?"}],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Good answer!", 100, 25)

        await coach_service_with_ws.chat(
            user_id=user_id, session_id=session_id, message="A function inside a function"
        )

        # First call should be typing indicator
        calls = ws_publisher.publish_to_user.call_args_list
        assert len(calls) == 2
        typing_call = calls[0]
        assert typing_call[0][0] == str(user_id)
        typing_msg = typing_call[0][1]
        assert typing_msg["type"] == "typing_indicator"
        assert typing_msg["session_id"] == session_id
        assert typing_msg["is_typing"] is True

    async def test_chat_publishes_coach_message(
        self, coach_service_with_ws, coach_llm, coach_cache, ws_publisher
    ):
        user_id = uuid4()
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "You are a Coach...",
            "messages": [{"role": "assistant", "content": "What is a closure?"}],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Good answer!", 100, 25)

        await coach_service_with_ws.chat(
            user_id=user_id, session_id=session_id, message="A function inside a function"
        )

        # Second call should be coach message
        calls = ws_publisher.publish_to_user.call_args_list
        coach_msg_call = calls[1]
        assert coach_msg_call[0][0] == str(user_id)
        msg = coach_msg_call[0][1]
        assert msg["type"] == "coach_message"
        assert msg["session_id"] == session_id
        assert msg["content"] == "Good answer!"
        assert msg["phase"] == "recap"

    async def test_chat_works_when_ws_publisher_fails(
        self, coach_service_with_ws, coach_llm, coach_cache, ws_publisher
    ):
        user_id = uuid4()
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "You are a Coach...",
            "messages": [{"role": "assistant", "content": "What is a closure?"}],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Good answer!", 100, 25)
        ws_publisher.publish_to_user.side_effect = Exception("WS gateway down")

        # Should NOT raise — WS is fire-and-forget
        result = await coach_service_with_ws.chat(
            user_id=user_id, session_id=session_id, message="A function inside a function"
        )

        assert isinstance(result, CoachMessage)
        assert result.content == "Good answer!"

    async def test_start_session_publishes_coach_message(
        self, coach_service_with_ws, coach_llm, coach_cache, ws_publisher, sample_mission
    ):
        user_id = uuid4()
        coach_llm.generate.return_value = (
            "Welcome! Let's start with a quick recap.",
            100,
            30,
        )

        result = await coach_service_with_ws.start_session(
            user_id=user_id, mission=sample_mission
        )

        calls = ws_publisher.publish_to_user.call_args_list
        assert len(calls) >= 1
        # Last call should be coach message
        msg = calls[-1][0][1]
        assert msg["type"] == "coach_message"
        assert msg["session_id"] == result.session_id
        assert msg["content"] == "Welcome! Let's start with a quick recap."

    async def test_coach_without_ws_publisher_still_works(
        self, coach_llm, coach_cache
    ):
        """CoachService works without ws_publisher (backward compatible)."""
        settings = Settings()
        service = CoachService(llm=coach_llm, cache=coach_cache, settings=settings)

        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "You are a Coach...",
            "messages": [{"role": "assistant", "content": "Hi"}],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Great!", 50, 15)

        result = await service.chat(
            user_id=uuid4(), session_id=session_id, message="hello"
        )

        assert isinstance(result, CoachMessage)
        assert result.content == "Great!"
