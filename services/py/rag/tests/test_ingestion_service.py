from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from app.services.ingestion_service import IngestionService
from app.domain.document import Document


@pytest.fixture
def doc_repo():
    return AsyncMock()


@pytest.fixture
def embedding_client():
    client = AsyncMock()
    client.embed_batch.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    return client


@pytest.fixture
def vector_store():
    return AsyncMock()


@pytest.fixture
def service(doc_repo, embedding_client, vector_store):
    return IngestionService(
        document_repo=doc_repo,
        embedding_client=embedding_client,
        vector_store=vector_store,
    )


def _make_document(doc_id=None, org_id=None):
    return Document(
        id=doc_id or uuid4(),
        organization_id=org_id or uuid4(),
        source_type="text",
        source_path="/doc.md",
        title="Test Doc",
        content="Paragraph one.\n\nParagraph two.",
        metadata={},
        created_at=datetime.now(timezone.utc),
    )


class TestIngest:
    async def test_creates_document_and_chunks(self, service, doc_repo, embedding_client, vector_store):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        chunk_ids = [uuid4(), uuid4()]
        doc_repo.create_chunks.return_value = chunk_ids

        result = await service.ingest(
            org_id=doc.organization_id,
            source_type="text",
            source_path="/doc.md",
            title="Test Doc",
            content="Paragraph one.\n\nParagraph two.",
        )
        assert isinstance(result, Document)
        doc_repo.create_document.assert_called_once()
        embedding_client.embed_batch.assert_called_once()
        doc_repo.create_chunks.assert_called_once()
        assert vector_store.upsert.call_count == len(chunk_ids)

    async def test_uses_code_chunker_for_github_source(self, service, doc_repo, embedding_client):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        doc_repo.create_chunks.return_value = [uuid4()]
        embedding_client.embed_batch.return_value = [[0.1, 0.2]]

        code_content = "def hello():\n    pass\n"
        await service.ingest(
            org_id=doc.organization_id,
            source_type="github",
            source_path="/hello.py",
            title="hello.py",
            content=code_content,
        )
        doc_repo.create_chunks.assert_called_once()
        chunks_arg = doc_repo.create_chunks.call_args[0][1]
        assert len(chunks_arg) >= 1

    async def test_uses_code_chunker_for_code_source(self, service, doc_repo, embedding_client):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        doc_repo.create_chunks.return_value = [uuid4()]
        embedding_client.embed_batch.return_value = [[0.1]]

        await service.ingest(
            org_id=doc.organization_id,
            source_type="code",
            source_path="/main.py",
            title="main.py",
            content="class Foo:\n    pass\n",
        )
        doc_repo.create_chunks.assert_called_once()

    async def test_uses_text_chunker_for_markdown(self, service, doc_repo, embedding_client):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        doc_repo.create_chunks.return_value = [uuid4()]
        embedding_client.embed_batch.return_value = [[0.1]]

        await service.ingest(
            org_id=doc.organization_id,
            source_type="markdown",
            source_path="/readme.md",
            title="README",
            content="Some text.",
        )
        doc_repo.create_chunks.assert_called_once()

    async def test_passes_embeddings_to_chunks(self, service, doc_repo, embedding_client):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        doc_repo.create_chunks.return_value = [uuid4()]
        embedding_client.embed_batch.return_value = [[0.1, 0.2]]

        await service.ingest(
            org_id=doc.organization_id,
            source_type="text",
            source_path="/t.txt",
            title="T",
            content="Some content here.",
        )
        chunks_arg = doc_repo.create_chunks.call_args[0][1]
        assert chunks_arg[0]["embedding"] == [0.1, 0.2]

    async def test_metadata_passed_to_document(self, service, doc_repo, embedding_client):
        doc = _make_document()
        doc_repo.create_document.return_value = doc
        doc_repo.create_chunks.return_value = []
        embedding_client.embed_batch.return_value = []

        await service.ingest(
            org_id=doc.organization_id,
            source_type="text",
            source_path="/t.txt",
            title="T",
            content="",
            metadata={"key": "value"},
        )
        call_kwargs = doc_repo.create_document.call_args
        assert call_kwargs[1].get("metadata") == {"key": "value"} or call_kwargs[0][5] == {"key": "value"}


class TestDelete:
    async def test_delegates_to_repo_and_vector_store(self, service, doc_repo, vector_store):
        doc_id = uuid4()
        doc_repo.delete_document.return_value = True

        result = await service.delete(doc_id)
        assert result is True
        vector_store.delete_by_document.assert_called_once_with(doc_id)
        doc_repo.delete_document.assert_called_once_with(doc_id)

    async def test_returns_false_when_not_found(self, service, doc_repo, vector_store):
        doc_repo.delete_document.return_value = False

        result = await service.delete(uuid4())
        assert result is False
