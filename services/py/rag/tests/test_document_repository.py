from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
from datetime import datetime, timezone

import pytest

from app.repositories.document_repository import DocumentRepository
from app.domain.document import Document, Chunk


def _make_pool_with_conn(conn: AsyncMock) -> MagicMock:
    """Create a mock pool where acquire() returns an async context manager yielding conn."""
    pool = MagicMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool


def _make_doc_row(
    doc_id=None, org_id=None, source_type="text", source_path="/doc.md",
    title="Test", content="Hello", metadata=None,
):
    doc_id = doc_id or uuid4()
    org_id = org_id or uuid4()
    return {
        "id": doc_id,
        "organization_id": org_id,
        "source_type": source_type,
        "source_path": source_path,
        "title": title,
        "content": content,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc),
    }


class TestCreateDocument:
    async def test_creates_and_returns_document(self):
        org_id = uuid4()
        row = _make_doc_row(org_id=org_id)
        conn = AsyncMock()
        conn.fetchrow.return_value = row
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        doc = await repo.create_document(
            org_id=org_id,
            source_type="text",
            source_path="/doc.md",
            title="Test",
            content="Hello",
            metadata={},
        )
        assert isinstance(doc, Document)
        assert doc.organization_id == org_id
        assert doc.title == "Test"
        conn.fetchrow.assert_called_once()

    async def test_sql_uses_parameterized_query(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = _make_doc_row()
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        await repo.create_document(uuid4(), "text", "/a", "T", "C", {})
        sql = conn.fetchrow.call_args[0][0]
        assert "$1" in sql
        assert "$2" in sql


class TestCreateChunks:
    async def test_creates_chunks_returns_ids(self):
        doc_id = uuid4()
        chunk_ids = [uuid4(), uuid4()]
        conn = AsyncMock()
        conn.fetchval = AsyncMock(side_effect=chunk_ids)
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        chunks_data = [
            {"content": "chunk 1", "chunk_index": 0, "embedding": [0.1, 0.2], "metadata": {}},
            {"content": "chunk 2", "chunk_index": 1, "embedding": [0.3, 0.4], "metadata": {}},
        ]
        result = await repo.create_chunks(doc_id, chunks_data)
        assert len(result) == 2
        assert result == chunk_ids

    async def test_empty_chunks_returns_empty(self):
        conn = AsyncMock()
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        result = await repo.create_chunks(uuid4(), [])
        assert result == []


class TestGetDocument:
    async def test_returns_document_when_found(self):
        row = _make_doc_row()
        conn = AsyncMock()
        conn.fetchrow.return_value = row
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        doc = await repo.get_document(row["id"])
        assert isinstance(doc, Document)
        assert doc.id == row["id"]

    async def test_returns_none_when_not_found(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        result = await repo.get_document(uuid4())
        assert result is None


class TestGetDocumentsByOrg:
    async def test_returns_documents_list(self):
        rows = [_make_doc_row(), _make_doc_row()]
        conn = AsyncMock()
        conn.fetch.return_value = rows
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        docs = await repo.get_documents_by_org(uuid4(), limit=20, offset=0)
        assert len(docs) == 2
        assert all(isinstance(d, Document) for d in docs)

    async def test_uses_limit_and_offset(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        await repo.get_documents_by_org(uuid4(), limit=10, offset=5)
        sql = conn.fetch.call_args[0][0]
        assert "$2" in sql  # limit
        assert "$3" in sql  # offset


class TestDeleteDocument:
    async def test_returns_true_when_deleted(self):
        conn = AsyncMock()
        conn.execute.return_value = "DELETE 1"
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        result = await repo.delete_document(uuid4())
        assert result is True

    async def test_returns_false_when_not_found(self):
        conn = AsyncMock()
        conn.execute.return_value = "DELETE 0"
        pool = _make_pool_with_conn(conn)
        repo = DocumentRepository(pool)

        result = await repo.delete_document(uuid4())
        assert result is False
