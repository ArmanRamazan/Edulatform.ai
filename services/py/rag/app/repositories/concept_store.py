from __future__ import annotations

from uuid import UUID

import asyncpg


class ConceptStoreRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert_concept(
        self,
        org_id: UUID,
        name: str,
        description: str,
        source_document_id: UUID | None,
    ) -> UUID:
        sql = """
            INSERT INTO org_concepts (organization_id, name, description, source_document_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (organization_id, name)
            DO UPDATE SET description = EXCLUDED.description,
                          source_document_id = COALESCE(EXCLUDED.source_document_id, org_concepts.source_document_id)
            RETURNING id
        """
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, org_id, name, description, source_document_id)

    async def add_relationship(
        self,
        concept_id: UUID,
        related_concept_id: UUID,
        relationship_type: str = "related",
    ) -> None:
        sql = """
            INSERT INTO concept_relationships (concept_id, related_concept_id, relationship_type)
            VALUES ($1, $2, $3)
            ON CONFLICT (concept_id, related_concept_id) DO NOTHING
        """
        async with self._pool.acquire() as conn:
            await conn.execute(sql, concept_id, related_concept_id, relationship_type)

    async def count_by_org(self, org_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM org_concepts WHERE organization_id = $1",
                org_id,
            )

    async def get_org_concepts(self, org_id: UUID) -> list[dict]:
        sql = """
            SELECT id, organization_id, name, description, source_document_id, created_at
            FROM org_concepts
            WHERE organization_id = $1
            ORDER BY name
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, org_id)
        return [dict(r) for r in rows]

    async def get_relationships_by_org(self, org_id: UUID) -> list[dict]:
        sql = """
            SELECT cr.concept_id, cr.related_concept_id, cr.relationship_type
            FROM concept_relationships cr
            JOIN org_concepts oc ON cr.concept_id = oc.id
            WHERE oc.organization_id = $1
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, org_id)
        return [dict(r) for r in rows]
