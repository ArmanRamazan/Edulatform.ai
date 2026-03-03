import asyncio

import httpx
import structlog

from common.errors import AppError

logger = structlog.get_logger()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClient:
    def __init__(self, http_client: httpx.AsyncClient, api_key: str, model: str) -> None:
        self._http = http_client
        self._api_key = api_key
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str) -> tuple[str, int, int]:
        url = f"{GEMINI_API_URL}/{self._model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
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
