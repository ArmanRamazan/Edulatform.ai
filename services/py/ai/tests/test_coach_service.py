import json
import time
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.config import Settings
from app.domain.coach import CoachMessage, SessionResult
from app.domain.mission import (
    MissionBlueprint,
    RecapQuestion,
    CheckQuestion,
    CodeCase,
)
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.services.coach_service import CoachService


@pytest.fixture
def coach_settings():
    return Settings()


@pytest.fixture
def coach_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def coach_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def coach_service(coach_llm, coach_cache, coach_settings):
    return CoachService(llm=coach_llm, cache=coach_cache, settings=coach_settings)


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
            RecapQuestion(
                question="What is a first-class function?",
                expected_answer="A function that can be passed as argument",
                concept_ref="first-class-functions",
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
            CheckQuestion(
                question="Which is a valid decorator?",
                options=["@123", "@my_func", "@if", "@class"],
                correct_index=1,
                explanation="Decorators must be valid callable references",
            ),
            CheckQuestion(
                question="What does functools.wraps preserve?",
                options=["Speed", "Metadata", "Memory", "Types"],
                correct_index=1,
                explanation="wraps preserves the original function's metadata",
            ),
        ],
        code_case=CodeCase(
            code_snippet="def timer(func):\n    def wrapper(*args):\n        start = time.time()\n        result = func(*args)\n        print(time.time() - start)\n        return result\n    return wrapper",
            language="python",
            question="What happens if you apply @timer to an async function?",
            expected_answer="It won't work correctly because wrapper doesn't await the coroutine",
            source_path="examples/decorators.py",
        ),
    )


class TestStartSession:
    async def test_returns_coach_message_with_recap_phase(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = (
            "Welcome! Let's start with a quick recap. What is a closure?",
            100,
            30,
        )

        result = await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        assert isinstance(result, CoachMessage)
        assert result.phase == "recap"
        assert result.phase_progress == 1
        assert result.session_id is not None
        assert len(result.session_id) == 36
        assert "closure" in result.content.lower() or len(result.content) > 0

    async def test_saves_session_to_cache(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = (
            "Let's begin! What is a closure?",
            80,
            25,
        )

        result = await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        coach_cache.save_coach_session.assert_called_once()
        call_args = coach_cache.save_coach_session.call_args
        session_id = call_args[0][0]
        data = call_args[0][1]
        assert session_id == result.session_id
        assert "system_prompt" in data
        assert "messages" in data
        assert "phase" in data
        assert data["phase"] == "recap"

    async def test_system_prompt_contains_session_structure(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = ("Let's go!", 50, 20)

        await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "Phase 1 (RECAP)" in prompt
        assert "Phase 2 (READ)" in prompt
        assert "Phase 3 (CHECK)" in prompt
        assert "Phase 4 (PRACTICE)" in prompt
        assert "Phase 5 (WRAP-UP)" in prompt

    async def test_system_prompt_contains_socratic_rules(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = ("Hello!", 50, 20)

        await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "never give answers directly" in prompt.lower() or "don't give answers directly" in prompt.lower()
        assert "Socratic" in prompt or "guiding questions" in prompt.lower()

    async def test_system_prompt_includes_mission_content(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = ("Starting!", 50, 20)

        await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "Python Decorators" in prompt
        assert "What is a closure?" in prompt
        assert "Decorators are functions that modify other functions" in prompt

    async def test_personality_included_in_prompt(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = ("Hey there!", 50, 20)

        await coach_service.start_session(
            user_id=uuid4(),
            mission=sample_mission,
            personality="encouraging",
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "encouraging" in prompt.lower()

    async def test_default_personality_is_friendly(
        self, coach_service, coach_llm, coach_cache, sample_mission
    ):
        coach_llm.generate.return_value = ("Hi!", 50, 20)

        await coach_service.start_session(
            user_id=uuid4(), mission=sample_mission
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "friendly" in prompt.lower()


class TestChat:
    async def test_loads_session_and_returns_message(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "You are a Coach...",
            "messages": [
                {"role": "assistant", "content": "What is a closure?"},
            ],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = (
            "Good thinking! Can you give an example?",
            120,
            30,
        )

        result = await coach_service.chat(
            user_id=uuid4(), session_id=session_id, message="A function inside a function"
        )

        assert isinstance(result, CoachMessage)
        assert result.session_id == session_id
        assert "example" in result.content.lower()

    async def test_appends_messages_to_history(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System prompt here",
            "messages": [
                {"role": "assistant", "content": "What is a closure?"},
            ],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Great answer!", 100, 25)

        await coach_service.chat(
            user_id=uuid4(), session_id=session_id, message="My answer"
        )

        coach_cache.save_coach_session.assert_called_once()
        saved_data = coach_cache.save_coach_session.call_args[0][1]
        messages = saved_data["messages"]
        assert len(messages) == 3
        assert messages[1] == {"role": "user", "content": "My answer"}
        assert messages[2] == {"role": "assistant", "content": "Great answer!"}

    async def test_includes_full_conversation_in_prompt(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System prompt",
            "messages": [
                {"role": "assistant", "content": "What is a closure?"},
                {"role": "user", "content": "A captured function"},
                {"role": "assistant", "content": "Close! Can you elaborate?"},
            ],
            "phase": "recap",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Exactly right!", 150, 30)

        await coach_service.chat(
            user_id=uuid4(), session_id=session_id, message="It captures variables"
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "What is a closure?" in prompt
        assert "A captured function" in prompt
        assert "Can you elaborate?" in prompt
        assert "It captures variables" in prompt

    async def test_session_not_found_raises_error(
        self, coach_service, coach_cache
    ):
        from common.errors import AppError

        coach_cache.get_coach_session.return_value = None

        with pytest.raises(AppError, match="Session not found"):
            await coach_service.chat(
                user_id=uuid4(), session_id="nonexistent", message="hello"
            )

    async def test_phase_from_session_data(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System",
            "messages": [{"role": "assistant", "content": "Read this content..."}],
            "phase": "read",
            "started_at": time.time(),
            "mission": {"concept_name": "Decorators"},
        }
        coach_llm.generate.return_value = ("Good question about the reading!", 80, 20)

        result = await coach_service.chat(
            user_id=uuid4(), session_id=session_id, message="What does this mean?"
        )

        assert result.phase == "read"


class TestEndSession:
    async def test_returns_session_result(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        started = time.time() - 600  # 10 minutes ago
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System",
            "messages": [
                {"role": "assistant", "content": "Q1"},
                {"role": "user", "content": "A1"},
                {"role": "assistant", "content": "Good!"},
            ],
            "phase": "wrap-up",
            "started_at": started,
            "mission": {"concept_name": "Decorators"},
        }
        eval_json = json.dumps({
            "overall_score": 78,
            "concept_mastery_delta": 0.15,
            "strengths": ["Good understanding of closures"],
            "gaps": ["Needs practice with async decorators"],
        })
        coach_llm.generate.return_value = (eval_json, 200, 50)

        result = await coach_service.end_session(
            user_id=uuid4(), session_id=session_id
        )

        assert isinstance(result, SessionResult)
        assert result.session_id == session_id
        assert result.score == 78
        assert result.mastery_delta == 0.15
        assert result.duration_seconds >= 500  # approximately 10 min
        assert "Good understanding of closures" in result.strengths
        assert "Needs practice with async decorators" in result.gaps

    async def test_builds_evaluation_prompt(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System",
            "messages": [
                {"role": "assistant", "content": "Q"},
                {"role": "user", "content": "A"},
            ],
            "phase": "check",
            "started_at": time.time() - 300,
            "mission": {"concept_name": "Decorators"},
        }
        eval_json = json.dumps({
            "overall_score": 60,
            "concept_mastery_delta": 0.1,
            "strengths": [],
            "gaps": ["Everything"],
        })
        coach_llm.generate.return_value = (eval_json, 150, 40)

        await coach_service.end_session(
            user_id=uuid4(), session_id=session_id
        )

        prompt = coach_llm.generate.call_args[0][0]
        assert "rate" in prompt.lower() or "evaluate" in prompt.lower()
        assert "overall_score" in prompt
        assert "concept_mastery_delta" in prompt
        assert "strengths" in prompt
        assert "gaps" in prompt

    async def test_session_not_found_raises_error(
        self, coach_service, coach_cache
    ):
        from common.errors import AppError

        coach_cache.get_coach_session.return_value = None

        with pytest.raises(AppError, match="Session not found"):
            await coach_service.end_session(
                user_id=uuid4(), session_id="nonexistent"
            )

    async def test_handles_markdown_fenced_json(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System",
            "messages": [{"role": "assistant", "content": "Done!"}],
            "phase": "wrap-up",
            "started_at": time.time() - 900,
            "mission": {"concept_name": "Decorators"},
        }
        fenced_json = '```json\n{"overall_score": 85, "concept_mastery_delta": 0.2, "strengths": ["Great"], "gaps": []}\n```'
        coach_llm.generate.return_value = (fenced_json, 180, 45)

        result = await coach_service.end_session(
            user_id=uuid4(), session_id=session_id
        )

        assert result.score == 85
        assert result.mastery_delta == 0.2

    async def test_deletes_session_from_cache(
        self, coach_service, coach_llm, coach_cache
    ):
        session_id = str(uuid4())
        coach_cache.get_coach_session.return_value = {
            "system_prompt": "System",
            "messages": [],
            "phase": "wrap-up",
            "started_at": time.time() - 100,
            "mission": {"concept_name": "Decorators"},
        }
        eval_json = json.dumps({
            "overall_score": 70,
            "concept_mastery_delta": 0.1,
            "strengths": [],
            "gaps": [],
        })
        coach_llm.generate.return_value = (eval_json, 100, 30)

        await coach_service.end_session(
            user_id=uuid4(), session_id=session_id
        )

        coach_cache.delete_coach_session.assert_called_once_with(session_id)
