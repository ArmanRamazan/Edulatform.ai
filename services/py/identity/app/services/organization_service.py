from __future__ import annotations

import re
from uuid import UUID

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.organization import Organization, OrgMember
from app.repositories.organization_repo import OrganizationRepository

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_VALID_ROLES = frozenset({"owner", "admin", "member"})


class OrganizationService:
    def __init__(self, repo: OrganizationRepository) -> None:
        self._repo = repo

    async def create_organization(
        self, name: str, slug: str, owner_user_id: UUID
    ) -> Organization:
        name = name.strip()
        if not name:
            raise AppError("Organization name cannot be empty")
        if len(name) > 200:
            raise AppError("Organization name too long")
        if not _SLUG_RE.match(slug):
            raise AppError("Invalid slug: must be lowercase letters, numbers, hyphens only, no leading/trailing hyphens")

        org = await self._repo.create(name=name, slug=slug, settings={})
        await self._repo.add_member(org.id, owner_user_id, "owner")
        return org

    async def get_organization(self, org_id: UUID) -> Organization:
        org = await self._repo.get_by_id(org_id)
        if not org:
            raise NotFoundError("Organization not found")
        return org

    async def get_organization_for_member(self, org_id: UUID, user_id: UUID) -> Organization:
        org = await self.get_organization(org_id)
        member = await self._repo.get_member(org_id, user_id)
        if not member:
            raise ForbiddenError("Not a member")
        return org

    async def invite_member(
        self,
        org_id: UUID,
        user_id: UUID,
        inviter_user_id: UUID,
        role: str = "member",
    ) -> OrgMember:
        if role not in _VALID_ROLES:
            raise AppError("Invalid role")

        inviter = await self._repo.get_member(org_id, inviter_user_id)
        if not inviter or inviter.role not in ("owner", "admin"):
            raise ForbiddenError("Only owner or admin can invite members")

        return await self._repo.add_member(org_id, user_id, role)

    async def remove_member(
        self, org_id: UUID, user_id: UUID, remover_user_id: UUID
    ) -> None:
        remover = await self._repo.get_member(org_id, remover_user_id)
        if not remover or remover.role not in ("owner", "admin"):
            raise ForbiddenError("Only owner or admin can remove members")

        target = await self._repo.get_member(org_id, user_id)
        if not target:
            raise NotFoundError("Member not found")
        if target.role == "owner":
            raise ForbiddenError("Cannot remove the owner")

        await self._repo.remove_member(org_id, user_id)

    async def get_my_organizations(self, user_id: UUID) -> list[Organization]:
        return await self._repo.get_user_orgs(user_id)

    async def get_members(
        self, org_id: UUID, user_id: UUID, limit: int, offset: int
    ) -> list[OrgMember]:
        member = await self._repo.get_member(org_id, user_id)
        if not member:
            raise ForbiddenError("Not a member")
        return await self._repo.get_members(org_id, limit, offset)
