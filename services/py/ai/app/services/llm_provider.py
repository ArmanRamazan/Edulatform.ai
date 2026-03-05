"""Abstract LLM provider and concrete implementations (Gemini, self-hosted OpenAI-compatible)."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

import httpx
import structlog

from common.errors import AppError

logger = structlog.get_logger()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMProvider(ABC):
    """Abstract base for LLM providers. All providers share the same interface."""

    @abstractmethod
    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        """Generate text from a prompt.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.

        Returns:
            Tuple of (generated_text, tokens_in, tokens_out).
        """
        ...


class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""

    def __init__(self, http_client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._http = http_client
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        url = f"{GEMINI_API_URL}/{self._model}:generateContent"

        contents = []
        if system:
            contents.append({"parts": [{"text": system}]})
        contents.append({"parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096,
            },
        }
        params = {"key": self._api_key}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._http.post(url, json=payload, params=params, timeout=30.0)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = AppError(f"Gemini API error: {resp.status_code}", status_code=502)
                    wait = 2 ** attempt
                    logger.warning("gemini_retry", status_code=resp.status_code, wait_seconds=wait, attempt=attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    raise AppError(f"Gemini API error: {resp.status_code} {resp.text}", status_code=502)

                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                tokens_in = usage.get("promptTokenCount", 0)
                tokens_out = usage.get("candidatesTokenCount", 0)
                return text, tokens_in, tokens_out
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("gemini_http_error", error=str(exc), wait_seconds=wait)
                await asyncio.sleep(wait)

        raise AppError(f"Gemini API unavailable after 3 retries: {last_exc}", status_code=502)


class SelfHostedProvider(LLMProvider):
    """OpenAI-compatible self-hosted LLM provider (vLLM, Ollama, text-generation-inference)."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str = "default",
        api_key: str | None = None,
    ) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    async def complete(self, prompt: str, system: str = "") -> tuple[str, int, int]:
        url = f"{self._base_url}/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._http.post(url, json=payload, headers=headers, timeout=60.0)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = AppError(f"Self-hosted LLM error: {resp.status_code}", status_code=502)
                    wait = 2 ** attempt
                    logger.warning(
                        "self_hosted_retry",
                        status_code=resp.status_code,
                        wait_seconds=wait,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    raise AppError(
                        f"Self-hosted LLM error: {resp.status_code} {resp.text}",
                        status_code=502,
                    )

                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)
                return text, tokens_in, tokens_out
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning("self_hosted_http_error", error=str(exc), wait_seconds=wait)
                await asyncio.sleep(wait)

        raise AppError(f"Self-hosted LLM unavailable after 3 retries: {last_exc}", status_code=502)
