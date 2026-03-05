from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.document import Document


class DocumentRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create_document(
        self,
        org_id: UUID,
        source_type: str,
        source_path: str,
        title: str,
        content: str,
        metadata: dict,
    ) -> Document:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (organization_id, source_type, source_path, title, content, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, organization_id, source_type, source_path, title, content, metadata, created_at
                """,
                org_id,
                source_type,
                source_path,
                title,
                content,
                json.dumps(metadata),
            )
        return self._row_to_document(row)

    async def create_chunks(
        self,
        document_id: UUID,
        chunks: list[dict],
    ) -> list[UUID]:
        if not chunks:
            return []

        ids: list[UUID] = []
        async with self._pool.acquire() as conn:
            for chunk in chunks:
                embedding_str = "[" + ",".join(str(v) for v in chunk["embedding"]) + "]"
                chunk_id = await conn.fetchval(
                    """
                    INSERT INTO chunks (document_id, content, chunk_index, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    document_id,
                    chunk["content"],
                    chunk["chunk_index"],
                    embedding_str,
                    json.dumps(chunk.get("metadata", {})),
                )
                ids.append(chunk_id)
        return ids

    async def get_document(self, document_id: UUID) -> Document | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, organization_id, source_type, source_path, title, content, metadata, created_at
                FROM documents WHERE id = $1
                """,
                document_id,
            )
        if row is None:
            return None
        return self._row_to_document(row)

    async def get_documents_by_org(
        self,
        org_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Document]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, organization_id, source_type, source_path, title, content, metadata, created_at
                FROM documents WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                org_id,
                limit,
                offset,
            )
        return [self._row_to_document(r) for r in rows]

    async def count_by_org(self, org_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM documents WHERE organization_id = $1",
                org_id,
            )

    async def count_chunks_by_org(self, org_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT COUNT(*) FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.organization_id = $1
                """,
                org_id,
            )

    async def last_updated_by_org(self, org_id: UUID) -> datetime | None:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT MAX(created_at) FROM documents WHERE organization_id = $1",
                org_id,
            )

    async def delete_chunks_by_document(self, document_id: UUID) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM chunks WHERE document_id = $1",
                document_id,
            )

    async def delete_document(self, document_id: UUID) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM documents WHERE id = $1",
                document_id,
            )
        return result == "DELETE 1"

    @staticmethod
    def _row_to_document(row: dict) -> Document:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return Document(
            id=row["id"],
            organization_id=row["organization_id"],
            source_type=row["source_type"],
            source_path=row["source_path"],
            title=row["title"],
            content=row["content"],
            metadata=metadata,
            created_at=row["created_at"],
        )
