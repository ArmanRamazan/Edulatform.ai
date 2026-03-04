from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

import pytest

from app.repositories.concept_store import ConceptStoreRepository


def _make_pool_with_conn(conn: AsyncMock) -> MagicMock:
    """Create a mock pool where acquire() returns an async context manager yielding conn."""
    pool = MagicMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool


class TestUpsertConcept:
    async def test_inserts_and_returns_id(self):
        concept_id = uuid4()
        conn = AsyncMock()
        conn.fetchval.return_value = concept_id
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        result = await repo.upsert_concept(
            org_id=uuid4(),
            name="Dependency Injection",
            description="A design pattern",
            source_document_id=uuid4(),
        )
        assert result == concept_id
        conn.fetchval.assert_called_once()

    async def test_sql_uses_on_conflict(self):
        conn = AsyncMock()
        conn.fetchval.return_value = uuid4()
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.upsert_concept(uuid4(), "Test", "Desc", uuid4())
        sql = conn.fetchval.call_args[0][0].upper()
        assert "ON CONFLICT" in sql

    async def test_uses_parameterized_query(self):
        conn = AsyncMock()
        conn.fetchval.return_value = uuid4()
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.upsert_concept(uuid4(), "Test", "Desc", uuid4())
        sql = conn.fetchval.call_args[0][0]
        assert "$1" in sql
        assert "$2" in sql

    async def test_handles_none_source_document(self):
        concept_id = uuid4()
        conn = AsyncMock()
        conn.fetchval.return_value = concept_id
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        result = await repo.upsert_concept(uuid4(), "Test", "Desc", None)
        assert result == concept_id


class TestAddRelationship:
    async def test_inserts_relationship(self):
        conn = AsyncMock()
        conn.execute.return_value = "INSERT 0 1"
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.add_relationship(uuid4(), uuid4(), "related")
        conn.execute.assert_called_once()

    async def test_sql_uses_on_conflict_do_nothing(self):
        conn = AsyncMock()
        conn.execute.return_value = "INSERT 0 1"
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.add_relationship(uuid4(), uuid4(), "related")
        sql = conn.execute.call_args[0][0].upper()
        assert "ON CONFLICT" in sql
        assert "DO NOTHING" in sql

    async def test_uses_parameterized_query(self):
        conn = AsyncMock()
        conn.execute.return_value = "INSERT 0 1"
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.add_relationship(uuid4(), uuid4(), "related")
        sql = conn.execute.call_args[0][0]
        assert "$1" in sql
        assert "$3" in sql


class TestGetOrgConcepts:
    async def test_returns_concepts_list(self):
        rows = [
            {
                "id": uuid4(),
                "organization_id": uuid4(),
                "name": "FastAPI",
                "description": "Web framework",
                "source_document_id": uuid4(),
                "created_at": datetime.now(timezone.utc),
            },
            {
                "id": uuid4(),
                "organization_id": uuid4(),
                "name": "SQLAlchemy",
                "description": "ORM",
                "source_document_id": uuid4(),
                "created_at": datetime.now(timezone.utc),
            },
        ]
        conn = AsyncMock()
        conn.fetch.return_value = rows
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        result = await repo.get_org_concepts(uuid4())
        assert len(result) == 2
        assert result[0]["name"] == "FastAPI"

    async def test_returns_empty_when_no_concepts(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        result = await repo.get_org_concepts(uuid4())
        assert result == []

    async def test_uses_parameterized_query(self):
        conn = AsyncMock()
        conn.fetch.return_value = []
        pool = _make_pool_with_conn(conn)
        repo = ConceptStoreRepository(pool)

        await repo.get_org_concepts(uuid4())
        sql = conn.fetch.call_args[0][0]
        assert "$1" in sql
