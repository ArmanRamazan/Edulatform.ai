from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.organization import Organization, OrgMember

_ORG_COLUMNS = "id, name, slug, logo_url, settings, is_active, created_at"
_MEMBER_COLUMNS = "id, organization_id, user_id, role, joined_at"


class OrganizationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, name: str, slug: str, settings: dict | None = None) -> Organization:
        try:
            row = await self._pool.fetchrow(
                f"INSERT INTO organizations (name, slug, settings) VALUES ($1, $2, $3::jsonb) RETURNING {_ORG_COLUMNS}",
                name,
                slug,
                _encode_settings(settings),
            )
        except asyncpg.UniqueViolationError:
            raise ConflictError("Organization slug already exists")
        return self._to_org(row)

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ORG_COLUMNS} FROM organizations WHERE id = $1",
            org_id,
        )
        return self._to_org(row) if row else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ORG_COLUMNS} FROM organizations WHERE slug = $1",
            slug,
        )
        return self._to_org(row) if row else None

    async def add_member(self, org_id: UUID, user_id: UUID, role: str = "member") -> OrgMember:
        try:
            row = await self._pool.fetchrow(
                f"INSERT INTO org_members (organization_id, user_id, role) VALUES ($1, $2, $3) RETURNING {_MEMBER_COLUMNS}",
                org_id,
                user_id,
                role,
            )
        except asyncpg.UniqueViolationError:
            raise ConflictError("User is already a member")
        return self._to_member(row)

    async def remove_member(self, org_id: UUID, user_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM org_members WHERE organization_id = $1 AND user_id = $2",
            org_id,
            user_id,
        )
        return result == "DELETE 1"

    async def get_member(self, org_id: UUID, user_id: UUID) -> OrgMember | None:
        row = await self._pool.fetchrow(
            f"SELECT {_MEMBER_COLUMNS} FROM org_members WHERE organization_id = $1 AND user_id = $2",
            org_id,
            user_id,
        )
        return self._to_member(row) if row else None

    async def get_members(self, org_id: UUID, limit: int, offset: int) -> list[OrgMember]:
        rows = await self._pool.fetch(
            f"SELECT {_MEMBER_COLUMNS} FROM org_members WHERE organization_id = $1 ORDER BY joined_at LIMIT $2 OFFSET $3",
            org_id,
            limit,
            offset,
        )
        return [self._to_member(r) for r in rows]

    async def get_user_orgs(self, user_id: UUID) -> list[Organization]:
        rows = await self._pool.fetch(
            f"SELECT o.{_ORG_COLUMNS.replace(', ', ', o.')} FROM organizations o "
            "JOIN org_members m ON o.id = m.organization_id "
            "WHERE m.user_id = $1 ORDER BY o.created_at DESC",
            user_id,
        )
        return [self._to_org(r) for r in rows]

    @staticmethod
    def _to_org(row: asyncpg.Record) -> Organization:
        import json
        settings_raw = row["settings"]
        if isinstance(settings_raw, str):
            settings = json.loads(settings_raw)
        elif isinstance(settings_raw, dict):
            settings = settings_raw
        else:
            settings = {}
        return Organization(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            logo_url=row["logo_url"],
            settings=settings,
            is_active=row["is_active"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_member(row: asyncpg.Record) -> OrgMember:
        return OrgMember(
            id=row["id"],
            organization_id=row["organization_id"],
            user_id=row["user_id"],
            role=row["role"],
            joined_at=row["joined_at"],
        )


def _encode_settings(settings: dict | None) -> str:
    import json
    return json.dumps(settings or {})
