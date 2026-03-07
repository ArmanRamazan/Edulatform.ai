"""Tests for OpenAIProvider, ClaudeProvider, and multi-provider LLMResolver logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.repositories.cache import AICache
from app.services.llm_provider import (
    ClaudeProvider,
    LLMProvider,
    MockLLMProvider,
    OpenAIProvider,
)
from app.services.llm_resolver import LLMResolver


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_openai_client():
    client = AsyncMock()
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello from OpenAI"
    response.usage.prompt_tokens = 12
    response.usage.completion_tokens = 7
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture
def openai_provider(mock_openai_client):
    return OpenAIProvider(client=mock_openai_client, model="gpt-4o-mini")


async def test_openai_provider_is_llm_provider(openai_provider):
    assert isinstance(openai_provider, LLMProvider)


async def test_openai_provider_complete_returns_text_and_tokens(openai_provider, mock_openai_client):
    text, tokens_in, tokens_out = await openai_provider.complete("tell me about Python")

    assert text == "Hello from OpenAI"
    assert tokens_in == 12
    assert tokens_out == 7


async def test_openai_provider_sends_user_message(openai_provider, mock_openai_client):
    await openai_provider.complete("my prompt")

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "my prompt"


async def test_openai_provider_sends_system_message_when_provided(openai_provider, mock_openai_client):
    await openai_provider.complete("my prompt", system="you are a tutor")

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "you are a tutor"
    assert messages[1]["role"] == "user"


async def test_openai_provider_no_system_message_when_empty(openai_provider, mock_openai_client):
    await openai_provider.complete("my prompt")

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


async def test_openai_provider_uses_correct_model(openai_provider, mock_openai_client):
    await openai_provider.complete("test")

    call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"


async def test_openai_provider_raises_app_error_on_failure(mock_openai_client):
    from common.errors import AppError

    mock_openai_client.chat.completions.create.side_effect = Exception("connection error")
    provider = OpenAIProvider(client=mock_openai_client, model="gpt-4o-mini")

    with pytest.raises(AppError):
        await provider.complete("test")


# ---------------------------------------------------------------------------
# ClaudeProvider
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_anthropic_client():
    client = AsyncMock()
    response = MagicMock()
    response.content = [MagicMock()]
    response.content[0].text = "Hello from Claude"
    response.usage.input_tokens = 9
    response.usage.output_tokens = 4
    client.messages.create.return_value = response
    return client


@pytest.fixture
def claude_provider(mock_anthropic_client):
    return ClaudeProvider(client=mock_anthropic_client, model="claude-sonnet-4-20250514")


async def test_claude_provider_is_llm_provider(claude_provider):
    assert isinstance(claude_provider, LLMProvider)


async def test_claude_provider_complete_returns_text_and_tokens(claude_provider, mock_anthropic_client):
    text, tokens_in, tokens_out = await claude_provider.complete("explain closures")

    assert text == "Hello from Claude"
    assert tokens_in == 9
    assert tokens_out == 4


async def test_claude_provider_sends_user_message(claude_provider, mock_anthropic_client):
    await claude_provider.complete("my prompt")

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "my prompt"


async def test_claude_provider_sends_system_when_provided(claude_provider, mock_anthropic_client):
    await claude_provider.complete("my prompt", system="you are a coding coach")

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["system"] == "you are a coding coach"


async def test_claude_provider_no_system_key_when_empty(claude_provider, mock_anthropic_client):
    await claude_provider.complete("my prompt")

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert "system" not in call_kwargs


async def test_claude_provider_uses_correct_model(claude_provider, mock_anthropic_client):
    await claude_provider.complete("test")

    call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-20250514"


async def test_claude_provider_raises_app_error_on_failure(mock_anthropic_client):
    from common.errors import AppError

    mock_anthropic_client.messages.create.side_effect = Exception("api error")
    provider = ClaudeProvider(client=mock_anthropic_client, model="claude-sonnet-4-20250514")

    with pytest.raises(AppError):
        await provider.complete("test")


# ---------------------------------------------------------------------------
# LLMResolver — multi-provider selection
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_http():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


def _make_resolver(mock_cache, mock_http, **settings_overrides) -> LLMResolver:
    """Build a resolver with explicit settings values to bypass env var defaults."""
    defaults = {
        "database_url": "postgresql://test:test@localhost:5432/test",
        "gemini_api_key": "",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "llm_provider": "",
    }
    defaults.update(settings_overrides)
    settings = Settings(**defaults)
    return LLMResolver(settings=settings, cache=mock_cache, http_client=mock_http)


async def test_resolver_llm_provider_mock_returns_mock(mock_cache, mock_http):
    resolver = _make_resolver(mock_cache, mock_http, llm_provider="mock")

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, MockLLMProvider)


async def test_resolver_llm_provider_openai_returns_openai(mock_cache, mock_http):
    mock_cache.get_llm_config.return_value = None
    resolver = _make_resolver(
        mock_cache, mock_http, llm_provider="openai", openai_api_key="sk-test"
    )

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, OpenAIProvider)


async def test_resolver_llm_provider_claude_returns_claude(mock_cache, mock_http):
    mock_cache.get_llm_config.return_value = None
    resolver = _make_resolver(
        mock_cache, mock_http, llm_provider="claude", anthropic_api_key="ant-test"
    )

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, ClaudeProvider)


async def test_resolver_autodetect_openai_when_only_openai_key_set(mock_cache, mock_http):
    mock_cache.get_llm_config.return_value = None
    resolver = _make_resolver(
        mock_cache, mock_http, gemini_api_key="", openai_api_key="sk-test"
    )

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, OpenAIProvider)


async def test_resolver_autodetect_claude_when_only_anthropic_key_set(mock_cache, mock_http):
    mock_cache.get_llm_config.return_value = None
    resolver = _make_resolver(
        mock_cache, mock_http, gemini_api_key="", anthropic_api_key="ant-test"
    )

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, ClaudeProvider)


async def test_resolver_fallback_to_mock_when_no_keys(mock_cache, mock_http):
    resolver = _make_resolver(mock_cache, mock_http)

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, MockLLMProvider)


async def test_resolver_explicit_provider_beats_autodetect(mock_cache, mock_http):
    """LLM_PROVIDER=claude wins even if gemini_api_key is also present."""
    mock_cache.get_llm_config.return_value = None
    resolver = _make_resolver(
        mock_cache,
        mock_http,
        llm_provider="claude",
        gemini_api_key="gemini-key",
        anthropic_api_key="ant-test",
    )

    provider = await resolver.resolve("org-1", "internal")

    assert isinstance(provider, ClaudeProvider)
