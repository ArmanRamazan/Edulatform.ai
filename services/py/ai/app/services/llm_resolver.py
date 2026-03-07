"""LLM resolver: picks the correct LLM provider based on org configuration."""
from __future__ import annotations

import json

import structlog

from common.errors import AppError
from app.config import Settings
from app.domain.llm_config import LLMConfig
from app.repositories.cache import AICache
from app.services.llm_provider import (
    ClaudeProvider,
    GeminiProvider,
    LLMProvider,
    MockLLMProvider,
    OpenAIProvider,
    SelfHostedProvider,
)

logger = structlog.get_logger()

_LLM_CONFIG_TTL = 300  # 5 minutes


def validate_llm_config(config: LLMConfig) -> None:
    """Validate LLM config business rules. Raises AppError on violation."""
    if config.data_isolation == "strict" and config.internal_provider != "self_hosted":
        raise AppError(
            "strict data isolation requires internal_provider=self_hosted",
            status_code=400,
        )
    if config.internal_provider == "self_hosted" and not config.internal_model_url:
        raise AppError(
            "self_hosted provider requires internal_model_url",
            status_code=400,
        )


class LLMResolver:
    """Resolves the appropriate LLM provider for an organization and purpose."""

    def __init__(
        self,
        settings: Settings,
        cache: AICache,
        http_client: "httpx.AsyncClient",
    ) -> None:
        self._settings = settings
        self._cache = cache
        self._http = http_client

    async def resolve(self, org_id: str, purpose: str) -> LLMProvider:
        """Resolve the LLM provider for a given org and purpose.

        Args:
            org_id: Organization ID.
            purpose: "internal" (org-specific content) or "external" (public/search).

        Returns:
            An LLMProvider instance. Falls back to MockLLMProvider when no API key is set.
        """
        default = self._make_default_provider()

        if isinstance(default, MockLLMProvider):
            return default

        config = await self._load_config(org_id)

        if purpose == "external":
            return default

        if config.internal_provider == "self_hosted" and config.internal_model_url:
            return SelfHostedProvider(
                http_client=self._http,
                base_url=config.internal_model_url,
            )

        return default

    def resolve_from_config(self, config: LLMConfig) -> LLMProvider:
        """Resolve provider directly from a config (for connection testing)."""
        if config.internal_provider == "self_hosted" and config.internal_model_url:
            return SelfHostedProvider(
                http_client=self._http,
                base_url=config.internal_model_url,
            )
        return self._make_default_provider()

    async def _load_config(self, org_id: str) -> LLMConfig:
        raw = await self._cache.get_llm_config(org_id)
        if raw is None:
            return LLMConfig()

        try:
            data = json.loads(raw)
            return LLMConfig.from_dict(data)
        except (json.JSONDecodeError, TypeError):
            logger.warning("invalid_llm_config_in_cache", org_id=org_id)
            return LLMConfig()

    def _make_default_provider(self) -> LLMProvider:
        """Select system-level provider: explicit env var > API key auto-detect > mock."""
        specified = self._settings.llm_provider

        if specified == "mock":
            return MockLLMProvider()
        if specified == "openai":
            return self._make_openai()
        if specified == "claude":
            return self._make_claude()
        if specified == "gemini":
            return self._make_gemini()

        # Auto-detect from API keys (gemini first for backward compatibility)
        if self._settings.gemini_api_key:
            return self._make_gemini()
        if self._settings.openai_api_key:
            return self._make_openai()
        if self._settings.anthropic_api_key:
            return self._make_claude()

        logger.info("mock_llm_active", reason="no API key configured")
        return MockLLMProvider()

    def _make_gemini(self) -> GeminiProvider:
        return GeminiProvider(
            http_client=self._http,
            api_key=self._settings.gemini_api_key,
            model=self._settings.gemini_model,
        )

    def _make_openai(self) -> OpenAIProvider:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._settings.openai_api_key)
        return OpenAIProvider(client=client, model=self._settings.openai_model)

    def _make_claude(self) -> ClaudeProvider:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        return ClaudeProvider(client=client, model=self._settings.claude_model)
