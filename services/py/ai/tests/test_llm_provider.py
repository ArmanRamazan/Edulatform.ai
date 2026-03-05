"""Tests for LLM provider abstraction: GeminiProvider, SelfHostedProvider, LLMResolver."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import Settings
from app.domain.llm_config import LLMConfig
from app.repositories.cache import AICache
from app.services.llm_provider import GeminiProvider, SelfHostedProvider, LLMProvider
from app.services.llm_resolver import LLMResolver


# --- Domain: LLMConfig ---


def test_llm_config_defaults():
    config = LLMConfig()
    assert config.internal_provider == "gemini"
    assert config.internal_model_url is None
    assert config.external_provider == "gemini"
    assert config.embedding_provider == "gemini"
    assert config.data_isolation == "standard"


def test_llm_config_frozen():
    config = LLMConfig()
    with pytest.raises(AttributeError):
        config.internal_provider = "self_hosted"  # type: ignore[misc]


def test_llm_config_strict_isolation():
    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url="http://vllm:8000/v1",
        data_isolation="strict",
    )
    assert config.internal_provider == "self_hosted"
    assert config.data_isolation == "strict"


def test_llm_config_to_dict():
    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url="http://vllm:8000/v1",
        data_isolation="strict",
    )
    d = config.to_dict()
    assert d["internal_provider"] == "self_hosted"
    assert d["internal_model_url"] == "http://vllm:8000/v1"
    assert d["data_isolation"] == "strict"


def test_llm_config_from_dict():
    d = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
        "external_provider": "gemini",
        "embedding_provider": "gemini",
        "data_isolation": "strict",
    }
    config = LLMConfig.from_dict(d)
    assert config.internal_provider == "self_hosted"
    assert config.internal_model_url == "http://vllm:8000/v1"


def test_llm_config_from_dict_with_defaults():
    config = LLMConfig.from_dict({})
    assert config.internal_provider == "gemini"
    assert config.data_isolation == "standard"


# --- GeminiProvider ---


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def gemini_provider(mock_http_client):
    return GeminiProvider(
        http_client=mock_http_client,
        api_key="test-key",
        model="gemini-2.0-flash-lite",
    )


async def test_gemini_provider_is_llm_provider(gemini_provider):
    assert isinstance(gemini_provider, LLMProvider)


async def test_gemini_provider_complete(gemini_provider, mock_http_client):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Hello world"}]}}],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
    }
    mock_http_client.post.return_value = resp

    text, tokens_in, tokens_out = await gemini_provider.complete("test prompt")

    assert text == "Hello world"
    assert tokens_in == 10
    assert tokens_out == 5


async def test_gemini_provider_complete_with_system(gemini_provider, mock_http_client):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "response"}]}}],
        "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 3},
    }
    mock_http_client.post.return_value = resp

    text, _, _ = await gemini_provider.complete("user prompt", system="system prompt")
    assert text == "response"

    # Verify system prompt was included in request
    call_args = mock_http_client.post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    assert payload is not None


async def test_gemini_provider_retries_on_429(gemini_provider, mock_http_client):
    err_resp = MagicMock()
    err_resp.status_code = 429

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
        "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2},
    }

    mock_http_client.post.side_effect = [err_resp, ok_resp]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await gemini_provider.complete("test")

    assert text == "ok"


# --- SelfHostedProvider ---


@pytest.fixture
def self_hosted_provider(mock_http_client):
    return SelfHostedProvider(
        http_client=mock_http_client,
        base_url="http://vllm:8000/v1",
        model="my-model",
    )


async def test_self_hosted_provider_is_llm_provider(self_hosted_provider):
    assert isinstance(self_hosted_provider, LLMProvider)


async def test_self_hosted_provider_complete(self_hosted_provider, mock_http_client):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from vLLM"}}],
        "usage": {"prompt_tokens": 15, "completion_tokens": 8},
    }
    mock_http_client.post.return_value = resp

    text, tokens_in, tokens_out = await self_hosted_provider.complete("test prompt")

    assert text == "Hello from vLLM"
    assert tokens_in == 15
    assert tokens_out == 8

    # Verify OpenAI-compatible API format
    call_args = mock_http_client.post.call_args
    url = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
    assert "chat/completions" in url


async def test_self_hosted_provider_with_system_prompt(self_hosted_provider, mock_http_client):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": "response"}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 5},
    }
    mock_http_client.post.return_value = resp

    await self_hosted_provider.complete("user msg", system="system msg")

    call_args = mock_http_client.post.call_args
    payload = call_args.kwargs.get("json") or call_args[1].get("json")
    messages = payload["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "system msg"
    assert messages[1]["role"] == "user"


async def test_self_hosted_provider_error_raises(self_hosted_provider, mock_http_client):
    from common.errors import AppError

    resp = MagicMock()
    resp.status_code = 500
    resp.text = "Internal Server Error"

    ok_resp = MagicMock()
    ok_resp.status_code = 500
    ok_resp.text = "still failing"

    mock_http_client.post.side_effect = [resp, ok_resp, ok_resp]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(AppError, match="Self-hosted LLM"):
            await self_hosted_provider.complete("test")


async def test_self_hosted_provider_retries_on_server_error(self_hosted_provider, mock_http_client):
    err_resp = MagicMock()
    err_resp.status_code = 503
    err_resp.text = "Service Unavailable"

    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }

    mock_http_client.post.side_effect = [err_resp, ok_resp]

    with patch("asyncio.sleep", new_callable=AsyncMock):
        text, _, _ = await self_hosted_provider.complete("test")

    assert text == "ok"


# --- LLMResolver ---


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def resolver(settings, mock_cache, mock_http_client):
    return LLMResolver(
        settings=settings,
        cache=mock_cache,
        http_client=mock_http_client,
    )


async def test_resolver_default_returns_gemini(resolver):
    """When no org config exists, resolver returns GeminiProvider."""
    resolver._cache.get_llm_config.return_value = None

    provider = await resolver.resolve("org-123", "internal")

    assert isinstance(provider, GeminiProvider)


async def test_resolver_external_always_gemini(resolver):
    """External purpose always returns Gemini, even if org uses self_hosted internally."""
    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url="http://vllm:8000/v1",
        data_isolation="strict",
    )
    resolver._cache.get_llm_config.return_value = json.dumps(config.to_dict())

    provider = await resolver.resolve("org-123", "external")

    assert isinstance(provider, GeminiProvider)


async def test_resolver_internal_self_hosted(resolver):
    """When org has self_hosted config, internal purpose returns SelfHostedProvider."""
    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url="http://vllm:8000/v1",
        data_isolation="strict",
    )
    resolver._cache.get_llm_config.return_value = json.dumps(config.to_dict())

    provider = await resolver.resolve("org-123", "internal")

    assert isinstance(provider, SelfHostedProvider)


async def test_resolver_caches_config(resolver):
    """Resolver reads from cache, not DB on every call."""
    config = LLMConfig()
    resolver._cache.get_llm_config.return_value = json.dumps(config.to_dict())

    await resolver.resolve("org-123", "internal")
    await resolver.resolve("org-123", "internal")

    assert resolver._cache.get_llm_config.call_count == 2


async def test_resolver_missing_url_for_self_hosted_falls_back_to_gemini(resolver):
    """If self_hosted but no URL, fall back to Gemini."""
    config_data = {
        "internal_provider": "self_hosted",
        "internal_model_url": None,
        "external_provider": "gemini",
        "embedding_provider": "gemini",
        "data_isolation": "standard",
    }
    resolver._cache.get_llm_config.return_value = json.dumps(config_data)

    provider = await resolver.resolve("org-123", "internal")

    assert isinstance(provider, GeminiProvider)


# --- LLM Config validation ---


def test_validate_config_strict_requires_self_hosted():
    """Strict data isolation requires self_hosted internal provider."""
    from app.services.llm_resolver import validate_llm_config
    from common.errors import AppError

    config = LLMConfig(
        internal_provider="gemini",
        data_isolation="strict",
    )
    with pytest.raises(AppError, match="strict.*self_hosted"):
        validate_llm_config(config)


def test_validate_config_self_hosted_requires_url():
    """Self-hosted provider requires internal_model_url."""
    from app.services.llm_resolver import validate_llm_config
    from common.errors import AppError

    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url=None,
        data_isolation="standard",
    )
    with pytest.raises(AppError, match="internal_model_url"):
        validate_llm_config(config)


def test_validate_config_valid_standard():
    from app.services.llm_resolver import validate_llm_config

    config = LLMConfig()
    validate_llm_config(config)  # Should not raise


def test_validate_config_valid_strict():
    from app.services.llm_resolver import validate_llm_config

    config = LLMConfig(
        internal_provider="self_hosted",
        internal_model_url="http://vllm:8000/v1",
        data_isolation="strict",
    )
    validate_llm_config(config)  # Should not raise
