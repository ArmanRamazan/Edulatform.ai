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


class OrchestratorEmbeddingClient(EmbeddingClient):
    """Calls the Rust embedding-orchestrator service with fallback to direct API."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        orchestrator_url: str,
        fallback: EmbeddingClient,
    ) -> None:
        self._http = http_client
        self._url = orchestrator_url.rstrip("/")
        self._fallback = fallback

    async def embed(self, text: str) -> list[float]:
        try:
            return await self._call_single(text)
        except (httpx.HTTPError, httpx.HTTPStatusError):
            logger.warning("orchestrator_embed_fallback", reason="connection_or_http_error")
            return await self._fallback.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            return await self._call_batch(texts)
        except (httpx.HTTPError, httpx.HTTPStatusError):
            logger.warning("orchestrator_embed_batch_fallback", reason="connection_or_http_error")
            return await self._fallback.embed_batch(texts)

    async def _call_single(self, text: str) -> list[float]:
        last_exc: Exception | None = None
        for _attempt in range(2):
            try:
                resp = await self._http.post(
                    f"{self._url}/embed",
                    json={"text": text},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()["embedding"]
            except httpx.ConnectError as exc:
                last_exc = exc
                continue
        raise last_exc  # type: ignore[misc]

    async def _call_batch(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None
        for _attempt in range(2):
            try:
                resp = await self._http.post(
                    f"{self._url}/embed/batch",
                    json={"texts": texts},
                    timeout=60.0,
                )
                resp.raise_for_status()
                return resp.json()["embeddings"]
            except httpx.ConnectError as exc:
                last_exc = exc
                continue
        raise last_exc  # type: ignore[misc]


class StubEmbeddingClient(EmbeddingClient):
    def __init__(self, dimensions: int = 768) -> None:
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        return [0.0] * self._dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(text) for text in texts]
