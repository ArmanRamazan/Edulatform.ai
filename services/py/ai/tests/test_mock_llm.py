"""Tests for MockLLMProvider and LLMResolver fallback when no API key is configured."""
from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.config import Settings
from app.repositories.cache import AICache
from app.services.llm_provider import GeminiProvider, LLMProvider, MockLLMProvider
from app.services.llm_resolver import LLMResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def mock_http() -> AsyncMock:
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_cache() -> AsyncMock:
    return AsyncMock(spec=AICache)


# ---------------------------------------------------------------------------
# MockLLMProvider — interface
# ---------------------------------------------------------------------------


async def test_mock_provider_is_llm_provider(mock_provider: MockLLMProvider) -> None:
    """MockLLMProvider must satisfy the LLMProvider ABC."""
    assert isinstance(mock_provider, LLMProvider)


async def test_mock_provider_complete_returns_three_tuple(mock_provider: MockLLMProvider) -> None:
    """complete() must return (str, int, int)."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await mock_provider.complete("tell me something")

    text, tokens_in, tokens_out = result
    assert isinstance(text, str)
    assert isinstance(tokens_in, int)
    assert isinstance(tokens_out, int)


# ---------------------------------------------------------------------------
# MockLLMProvider — response routing
# ---------------------------------------------------------------------------


async def test_mock_provider_returns_mission_blueprint(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'mission' or 'blueprint' return valid JSON blueprint."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("design a mission blueprint for Python closures")

    data = json.loads(text)
    assert "concept_name" in data
    assert "phases" in data
    phases = data["phases"]
    assert isinstance(phases, dict)
    # All five phases must be present
    for phase in ("recap", "reading", "questions", "code_case", "wrap_up"):
        assert phase in phases, f"Missing phase: {phase}"


async def test_mock_provider_returns_coach_response(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'coach', 'session', or 'socratic' return non-empty text."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, tokens_in, tokens_out = await mock_provider.complete(
            "coach session: help the learner understand closures via socratic method"
        )

    assert isinstance(text, str)
    assert len(text) > 10
    assert 200 <= tokens_in <= 800
    assert 100 <= tokens_out <= 500


async def test_mock_provider_returns_quiz(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'quiz' or 'question' return JSON list with correct_answer field."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("generate quiz questions about Python decorators")

    data = json.loads(text)
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "correct_answer" in first
    assert "question" in first or "text" in first


async def test_mock_provider_returns_summary(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'summary' or 'summarize' return a non-trivial text string."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("summarize this lesson content about decorators")

    assert isinstance(text, str)
    assert len(text) > 20


async def test_mock_provider_returns_search_routing(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'search', 'route', or 'classify' return JSON with routing key."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("classify this search query: what is a closure?")

    data = json.loads(text)
    # At least one routing-related key must exist
    routing_keys = {"route", "type", "intent", "source"}
    assert routing_keys & data.keys(), f"No routing key found in: {data}"


async def test_mock_provider_returns_safe_for_moderation(mock_provider: MockLLMProvider) -> None:
    """Prompts mentioning 'moderate' or 'safety' return {\"safe\": true}."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("moderate this content for safety check")

    data = json.loads(text)
    assert data.get("safe") is True


async def test_mock_provider_returns_generic_for_unknown_prompt(mock_provider: MockLLMProvider) -> None:
    """Unknown prompts return a non-empty generic response."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await mock_provider.complete("what is the meaning of life?")

    assert isinstance(text, str)
    assert len(text) > 0


# ---------------------------------------------------------------------------
# MockLLMProvider — token counts
# ---------------------------------------------------------------------------


async def test_mock_provider_token_counts_are_in_expected_range(mock_provider: MockLLMProvider) -> None:
    """Token counts must fall within the documented random ranges."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        _, tokens_in, tokens_out = await mock_provider.complete("generate some content")

    assert 200 <= tokens_in <= 800, f"tokens_in={tokens_in} out of range [200, 800]"
    assert 100 <= tokens_out <= 500, f"tokens_out={tokens_out} out of range [100, 500]"


# ---------------------------------------------------------------------------
# MockLLMProvider — latency simulation
# ---------------------------------------------------------------------------


async def test_mock_provider_simulates_latency(mock_provider: MockLLMProvider) -> None:
    """complete() must take at least 0.3 seconds due to asyncio.sleep simulation."""
    start = time.monotonic()
    await mock_provider.complete("what is a closure in Python?")
    elapsed = time.monotonic() - start

    assert elapsed > 0.3, f"Expected > 0.3s latency, got {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# LLMResolver — fallback to MockLLMProvider
# ---------------------------------------------------------------------------


async def test_resolver_returns_mock_when_no_api_key(
    mock_cache: AsyncMock,
    mock_http: AsyncMock,
) -> None:
    """When gemini_api_key is empty, resolver must return MockLLMProvider."""
    settings = Settings(gemini_api_key="")
    resolver = LLMResolver(settings=settings, cache=mock_cache, http_client=mock_http)
    mock_cache.get_llm_config.return_value = None

    provider = await resolver.resolve("org-123", "internal")

    assert isinstance(provider, MockLLMProvider)


async def test_resolver_returns_mock_for_external_when_no_api_key(
    mock_cache: AsyncMock,
    mock_http: AsyncMock,
) -> None:
    """Mock fallback applies to external purpose too when no API key is set."""
    settings = Settings(gemini_api_key="")
    resolver = LLMResolver(settings=settings, cache=mock_cache, http_client=mock_http)
    mock_cache.get_llm_config.return_value = None

    provider = await resolver.resolve("org-123", "external")

    assert isinstance(provider, MockLLMProvider)


async def test_resolver_returns_gemini_when_api_key_set(
    mock_cache: AsyncMock,
    mock_http: AsyncMock,
) -> None:
    """When gemini_api_key is present, resolver must return GeminiProvider (not mock)."""
    settings = Settings(gemini_api_key="real-api-key-abc123")
    resolver = LLMResolver(settings=settings, cache=mock_cache, http_client=mock_http)
    mock_cache.get_llm_config.return_value = None

    provider = await resolver.resolve("org-123", "internal")

    assert isinstance(provider, GeminiProvider)
