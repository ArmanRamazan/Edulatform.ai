from __future__ import annotations

import json
from uuid import UUID

import asyncpg


class SearchRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def search(
        self,
        query_embedding: list[float],
        org_id: UUID,
        limit: int = 5,
    ) -> list[dict]:
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT c.id, c.content, c.metadata, c.chunk_index,
                       d.title AS document_title, d.source_type, d.source_path,
                       1 - (c.embedding <=> $1::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.organization_id = $2
                ORDER BY c.embedding <=> $1::vector
                LIMIT $3
                """,
                embedding_str,
                org_id,
                limit,
            )
        results: list[dict] = []
        for row in rows:
            metadata = row["metadata"]
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            results.append({
                "id": row["id"],
                "content": row["content"],
                "metadata": metadata,
                "chunk_index": row["chunk_index"],
                "document_title": row["document_title"],
                "source_type": row["source_type"],
                "source_path": row["source_path"],
                "similarity": row["similarity"],
            })
        return results
