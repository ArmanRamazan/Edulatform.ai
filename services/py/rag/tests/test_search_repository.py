from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.search_repository import SearchRepository


def _make_pool_with_conn(conn: AsyncMock) -> MagicMock:
    pool = MagicMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool


def _make_search_row(chunk_id=None, doc_title="Test Doc"):
    return {
        "id": chunk_id or uuid4(),
        "content": "Some chunk content here.",
        "metadata": {},
        "chunk_index": 0,
        "document_title": doc_title,
        "source_type": "text",
        "source_path": "/doc.md",
        "similarity": 0.92,
    }


class TestSearch:
    async def test_returns_list_of_dicts(self):
        rows = [_make_search_row(), _make_search_row()]
        conn = AsyncMock()
        conn.fetch.return_value = rows
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        results = await repo.search(
            query_embedding=[0.1, 0.2, 0.3],
            org_id=uuid4(),
            limit=5,
        )
        assert len(results) == 2
        assert results[0]["content"] == "Some chunk content here."
        assert results[0]["similarity"] == 0.92

    async def test_sql_uses_parameterized_query(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        await repo.search([0.1], uuid4(), limit=5)
        sql = conn.fetch.call_args[0][0]
        assert "$1" in sql
        assert "$2" in sql
        assert "$3" in sql

    async def test_sql_uses_cosine_distance(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        await repo.search([0.1], uuid4(), limit=5)
        sql = conn.fetch.call_args[0][0]
        assert "<=>" in sql

    async def test_joins_documents_table(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        await repo.search([0.1], uuid4(), limit=5)
        sql = conn.fetch.call_args[0][0]
        assert "JOIN documents" in sql

    async def test_filters_by_org_id(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        org_id = uuid4()
        await repo.search([0.1], org_id, limit=5)
        args = conn.fetch.call_args[0]
        assert org_id in args

    async def test_passes_embedding_as_string(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        await repo.search([0.1, 0.2, 0.3], uuid4(), limit=5)
        embedding_arg = conn.fetch.call_args[0][1]
        assert embedding_arg == "[0.1,0.2,0.3]"

    async def test_passes_limit(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        await repo.search([0.1], uuid4(), limit=10)
        args = conn.fetch.call_args[0]
        assert 10 in args

    async def test_empty_results(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        results = await repo.search([0.1], uuid4(), limit=5)
        assert results == []

    async def test_metadata_parsed_from_string(self):
        row = _make_search_row()
        row["metadata"] = '{"key": "value"}'
        conn = AsyncMock()
        conn.fetch.return_value = [row]
        pool = _make_pool_with_conn(conn)
        repo = SearchRepository(pool)

        results = await repo.search([0.1], uuid4(), limit=5)
        assert results[0]["metadata"] == {"key": "value"}
