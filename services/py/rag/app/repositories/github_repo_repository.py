from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

import asyncpg

from app.domain.github_repo import OrgGithubRepo


class OrgGithubRepoRepository(ABC):
    @abstractmethod
    async def upsert(
        self,
        organization_id: UUID,
        repo_url: str,
        branch: str,
    ) -> OrgGithubRepo: ...

    @abstractmethod
    async def list_by_repo_url(self, repo_url: str) -> list[OrgGithubRepo]: ...

    @abstractmethod
    async def list_by_org(self, organization_id: UUID) -> list[OrgGithubRepo]: ...

    @abstractmethod
    async def update_last_synced(self, repo_id: UUID, synced_at: datetime) -> None: ...


class SqlOrgGithubRepoRepository(OrgGithubRepoRepository):
    _COLUMNS = "id, organization_id, repo_url, branch, last_synced_at, created_at"

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def upsert(
        self,
        organization_id: UUID,
        repo_url: str,
        branch: str,
    ) -> OrgGithubRepo:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                INSERT INTO org_github_repos (organization_id, repo_url, branch)
                VALUES ($1, $2, $3)
                ON CONFLICT (organization_id, repo_url)
                DO UPDATE SET branch = EXCLUDED.branch
                RETURNING {self._COLUMNS}
                """,
                organization_id,
                repo_url,
                branch,
            )
        return self._to_entity(row)

    async def list_by_repo_url(self, repo_url: str) -> list[OrgGithubRepo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT {self._COLUMNS} FROM org_github_repos WHERE repo_url = $1",
                repo_url,
            )
        return [self._to_entity(r) for r in rows]

    async def list_by_org(self, organization_id: UUID) -> list[OrgGithubRepo]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT {self._COLUMNS} FROM org_github_repos
                WHERE organization_id = $1
                ORDER BY created_at DESC
                """,
                organization_id,
            )
        return [self._to_entity(r) for r in rows]

    async def update_last_synced(self, repo_id: UUID, synced_at: datetime) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE org_github_repos SET last_synced_at = $1 WHERE id = $2",
                synced_at,
                repo_id,
            )

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> OrgGithubRepo:
        return OrgGithubRepo(
            id=row["id"],
            organization_id=row["organization_id"],
            repo_url=row["repo_url"],
            branch=row["branch"],
            last_synced_at=row["last_synced_at"],
            created_at=row["created_at"],
        )
