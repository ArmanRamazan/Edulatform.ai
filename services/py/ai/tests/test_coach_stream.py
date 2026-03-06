"""Tests for SSE streaming endpoint: GET /ai/coach/stream/{session_id}.

TDD — tests written FIRST, implementation follows.

Route: GET /ai/coach/stream/{session_id}?message=<text>
Service method: CoachService.stream_response(session_id, message)
"""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.repositories.cache import AICache
from app.repositories.llm_client import GeminiClient
from app.services.coach_service import CoachService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(settings: Settings, user_id: str | None = None) -> str:
    payload = {
        "sub": user_id or str(uuid4()),
        "role": "student",
        "subscription_tier": "pro",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def _sse_events(*payloads: str):
    """Async generator that yields SSE event strings."""
    for payload in payloads:
        yield payload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def mock_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def mock_coach():
    return AsyncMock(spec=CoachService)


@pytest.fixture
async def client(settings, mock_cache, mock_llm, mock_coach):
    import app.main as main_module

    main_module.app_settings = settings
    main_module._credit_service = main_module.CreditService(cache=mock_cache)
    main_module._coach_service = mock_coach
    main_module._ai_service = main_module.AIService(mock_llm, mock_cache, settings)
    main_module._tutor_service = main_module.TutorService(mock_llm, mock_cache, settings)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Route-level tests (HTTP behaviour)
# ---------------------------------------------------------------------------


class TestCoachStreamRoute:
    async def test_coach_stream_returns_sse_content_type(
        self, client, settings, mock_coach
    ):
        mock_coach.stream_response = lambda **_: _sse_events(
            'data: {"token": "", "done": true, "full_text": "ok"}\n\n'
        )

        token = _make_token(settings)
        resp = await client.get(
            f"/ai/coach/stream/{uuid4()}",
            params={"message": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_coach_stream_sends_tokens(
        self, client, settings, mock_coach
    ):
        mock_coach.stream_response = lambda **_: _sse_events(
            'data: {"token": "Hello", "done": false}\n\n',
            'data: {"token": "world", "done": false}\n\n',
            'data: {"token": "", "done": true, "full_text": "Hello world"}\n\n',
        )

        token = _make_token(settings)
        resp = await client.get(
            f"/ai/coach/stream/{uuid4()}",
            params={"message": "teach me"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data_lines = [
            line for line in resp.text.splitlines() if line.startswith("data: ")
        ]
        parsed = [json.loads(line[len("data: "):]) for line in data_lines]
        token_events = [e for e in parsed if not e.get("done")]

        assert any(e["token"] == "Hello" for e in token_events)
        assert any(e["token"] == "world" for e in token_events)

    async def test_coach_stream_sends_done_event(
        self, client, settings, mock_coach
    ):
        full_text = "Great answer here"
        mock_coach.stream_response = lambda **_: _sse_events(
            'data: {"token": "Great", "done": false}\n\n',
            f'data: {{"token": "", "done": true, "full_text": "{full_text}"}}\n\n',
        )

        token = _make_token(settings)
        resp = await client.get(
            f"/ai/coach/stream/{uuid4()}",
            params={"message": "go"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data_lines = [
            line for line in resp.text.splitlines() if line.startswith("data: ")
        ]
        parsed = [json.loads(line[len("data: "):]) for line in data_lines]
        done_events = [e for e in parsed if e.get("done")]

        assert len(done_events) == 1
        assert done_events[0]["token"] == ""
        assert done_events[0]["full_text"] == full_text

    async def test_coach_stream_requires_auth(self, client):
        resp = await client.get(
            f"/ai/coach/stream/{uuid4()}",
            params={"message": "hello"},
        )
        assert resp.status_code in (401, 422)

    async def test_coach_stream_response_headers_include_cache_control(
        self, client, settings, mock_coach
    ):
        mock_coach.stream_response = lambda **_: _sse_events(
            'data: {"token": "", "done": true, "full_text": "ok"}\n\n'
        )

        token = _make_token(settings)
        resp = await client.get(
            f"/ai/coach/stream/{uuid4()}",
            params={"message": "hello"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        assert resp.headers.get("cache-control") == "no-cache"


# ---------------------------------------------------------------------------
# Service-level tests (CoachService.stream_response)
# ---------------------------------------------------------------------------


@pytest.fixture
def coach_llm():
    mock = AsyncMock(spec=GeminiClient)
    mock.model_name = "gemini-2.0-flash-lite"
    return mock


@pytest.fixture
def coach_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def coach_service(coach_llm, coach_cache, settings):
    return CoachService(llm=coach_llm, cache=coach_cache, settings=settings)


@pytest.fixture
def session_state():
    return {
        "system_prompt": "You are a Coach...",
        "messages": [{"role": "assistant", "content": "What is a closure?"}],
        "phase": "recap",
        "started_at": time.time(),
        "mission": {"concept_name": "Python Decorators"},
    }


class TestStreamResponse:
    async def test_yields_token_events_for_each_word(
        self, coach_service, coach_llm, coach_cache, session_state
    ):
        from unittest.mock import patch

        coach_cache.get_coach_session.return_value = session_state
        coach_llm.generate.return_value = ("Hello world", 100, 20)

        events = []
        with patch("asyncio.sleep"):
            async for event in coach_service.stream_response(
                session_id="sess-1", message="hi"
            ):
                events.append(event)

        data_lines = [e for e in events if e.startswith("data: ")]
        token_events = [
            json.loads(line[len("data: "):].strip())
            for line in data_lines
        ]
        non_done = [e for e in token_events if not e.get("done")]

        assert any(e["token"] == "Hello" for e in non_done)
        assert any(e["token"] == "world" for e in non_done)

    async def test_yields_done_event_with_full_text(
        self, coach_service, coach_llm, coach_cache, session_state
    ):
        from unittest.mock import patch

        coach_cache.get_coach_session.return_value = session_state
        coach_llm.generate.return_value = ("Think about closures", 100, 20)

        events = []
        with patch("asyncio.sleep"):
            async for event in coach_service.stream_response(
                session_id="sess-1", message="what?"
            ):
                events.append(event)

        data_lines = [e for e in events if e.startswith("data: ")]
        parsed = [json.loads(line[len("data: "):].strip()) for line in data_lines]
        done_events = [e for e in parsed if e.get("done")]

        assert len(done_events) == 1
        assert done_events[0]["full_text"] == "Think about closures"
        assert done_events[0]["token"] == ""

    async def test_sse_format_is_valid(
        self, coach_service, coach_llm, coach_cache, session_state
    ):
        """Each yielded event must conform to SSE format: 'data: <json>\\n\\n'."""
        from unittest.mock import patch

        coach_cache.get_coach_session.return_value = session_state
        coach_llm.generate.return_value = ("One two", 80, 15)

        events = []
        with patch("asyncio.sleep"):
            async for event in coach_service.stream_response(
                session_id="sess-1", message="go"
            ):
                events.append(event)

        for event in events:
            assert event.startswith("data: "), f"Event must start with 'data: ': {event!r}"
            assert event.endswith("\n\n"), f"Event must end with '\\n\\n': {event!r}"
            # JSON must be valid
            json_part = event[len("data: "):].strip()
            parsed = json.loads(json_part)
            assert "token" in parsed
            assert "done" in parsed

    async def test_session_not_found_raises_error(
        self, coach_service, coach_cache
    ):
        from common.errors import AppError

        coach_cache.get_coach_session.return_value = None

        with pytest.raises(AppError, match="Session not found"):
            async for _ in coach_service.stream_response(
                session_id="missing", message="hello"
            ):
                pass

    async def test_saves_assistant_reply_to_session(
        self, coach_service, coach_llm, coach_cache, session_state
    ):
        from unittest.mock import patch

        coach_cache.get_coach_session.return_value = session_state
        coach_llm.generate.return_value = ("Good point", 80, 15)

        with patch("asyncio.sleep"):
            async for _ in coach_service.stream_response(
                session_id="sess-1", message="my answer"
            ):
                pass

        coach_cache.save_coach_session.assert_called_once()
        saved_data = coach_cache.save_coach_session.call_args[0][1]
        messages = saved_data["messages"]
        assert any(
            m["role"] == "assistant" and m["content"] == "Good point"
            for m in messages
        )
