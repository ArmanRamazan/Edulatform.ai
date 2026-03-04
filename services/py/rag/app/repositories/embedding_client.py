import abc
import asyncio

import httpx
import structlog

from common.errors import AppError

logger = structlog.get_logger()

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class EmbeddingClient(abc.ABC):
    @abc.abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abc.abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbeddingClient(EmbeddingClient):
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = "text-embedding-004",
    ) -> None:
        self._http = http_client
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        url = f"{GEMINI_API_URL}/{self._model}:embedContent"
        payload = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
        }
        params = {"key": self._api_key}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await self._http.post(
                    url, json=payload, params=params, timeout=30.0
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = AppError(
                        f"Gemini embedding API error: {resp.status_code}",
                        status_code=502,
                    )
                    wait = 2**attempt
                    logger.warning(
                        "gemini_embedding_retry",
                        status_code=resp.status_code,
                        wait_seconds=wait,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    raise AppError(
                        f"Gemini embedding API error: {resp.status_code} {resp.text}",
                        status_code=502,
                    )
                data = resp.json()
                return data["embedding"]["values"]
            except httpx.HTTPError as exc:
                last_exc = exc
                wait = 2**attempt
                logger.warning(
                    "gemini_embedding_http_error",
                    error=str(exc),
                    wait_seconds=wait,
                )
                await asyncio.sleep(wait)

        raise AppError(
            f"Gemini embedding API unavailable after 3 retries: {last_exc}",
            status_code=502,
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]


class StubEmbeddingClient(EmbeddingClient):
    def __init__(self, dimensions: int = 768) -> None:
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        return [0.0] * self._dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]
