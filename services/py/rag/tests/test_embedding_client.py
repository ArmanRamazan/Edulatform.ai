import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.embedding import EmbeddingResult
from app.repositories.embedding_client import (
    EmbeddingClient,
    GeminiEmbeddingClient,
    StubEmbeddingClient,
)


class TestEmbeddingResult:
    def test_create(self) -> None:
        result = EmbeddingResult(
            text="hello",
            vector=[0.1, 0.2, 0.3],
            model="text-embedding-004",
            token_count=1,
        )
        assert result.text == "hello"
        assert result.vector == [0.1, 0.2, 0.3]
        assert result.model == "text-embedding-004"
        assert result.token_count == 1

    def test_frozen(self) -> None:
        result = EmbeddingResult(
            text="hello", vector=[0.1], model="m", token_count=1
        )
        with pytest.raises(AttributeError):
            result.text = "other"  # type: ignore[misc]


class TestStubEmbeddingClient:
    @pytest.fixture
    def stub(self) -> StubEmbeddingClient:
        return StubEmbeddingClient(dimensions=768)

    async def test_embed_returns_correct_dimensions(self, stub: StubEmbeddingClient) -> None:
        vector = await stub.embed("hello world")
        assert len(vector) == 768
        assert all(v == 0.0 for v in vector)

    async def test_embed_batch(self, stub: StubEmbeddingClient) -> None:
        vectors = await stub.embed_batch(["one", "two", "three"])
        assert len(vectors) == 3
        for v in vectors:
            assert len(v) == 768

    async def test_implements_abc(self, stub: StubEmbeddingClient) -> None:
        assert isinstance(stub, EmbeddingClient)


class TestGeminiEmbeddingClient:
    @pytest.fixture
    def mock_http(self) -> httpx.AsyncClient:
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def client(self, mock_http: httpx.AsyncClient) -> GeminiEmbeddingClient:
        return GeminiEmbeddingClient(
            http_client=mock_http,
            api_key="test-key",
            model="text-embedding-004",
        )

    async def test_embed_success(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "embedding": {"values": [0.1, 0.2, 0.3]},
        }
        mock_http.post.return_value = mock_resp

        vector = await client.embed("hello")

        assert vector == [0.1, 0.2, 0.3]
        mock_http.post.assert_called_once()
        call_kwargs = mock_http.post.call_args
        assert "embedContent" in call_kwargs.args[0]
        assert call_kwargs.kwargs["params"] == {"key": "test-key"}

    async def test_embed_batch_success(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "embedding": {"values": [0.5, 0.6]},
        }
        mock_http.post.return_value = mock_resp

        vectors = await client.embed_batch(["one", "two"])

        assert len(vectors) == 2
        assert vectors[0] == [0.5, 0.6]
        assert mock_http.post.call_count == 2

    async def test_embed_api_error_raises(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        mock_http.post.return_value = mock_resp

        with pytest.raises(Exception, match="Gemini"):
            await client.embed("hello")

    async def test_embed_retries_on_429(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"embedding": {"values": [1.0]}}

        mock_http.post.side_effect = [rate_limit_resp, ok_resp]

        vector = await client.embed("hello")
        assert vector == [1.0]
        assert mock_http.post.call_count == 2

    async def test_embed_retries_exhausted_raises(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        error_resp = MagicMock()
        error_resp.status_code = 500

        mock_http.post.return_value = error_resp

        with pytest.raises(Exception, match="unavailable"):
            await client.embed("hello")
        assert mock_http.post.call_count == 3

    async def test_embed_http_error_retries(
        self, client: GeminiEmbeddingClient, mock_http: AsyncMock
    ) -> None:
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"embedding": {"values": [0.1]}}

        mock_http.post.side_effect = [httpx.ConnectError("fail"), ok_resp]

        vector = await client.embed("hello")
        assert vector == [0.1]

    async def test_implements_abc(self, client: GeminiEmbeddingClient) -> None:
        assert isinstance(client, EmbeddingClient)
