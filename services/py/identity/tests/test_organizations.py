from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.errors import AppError, ConflictError, ForbiddenError, NotFoundError, register_error_handlers
from app.domain.organization import Organization, OrgMember


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_org(**overrides) -> Organization:
    defaults = dict(
        id=uuid4(),
        name="Acme Corp",
        slug="acme-corp",
        logo_url=None,
        settings={},
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Organization(**defaults)


def _make_member(**overrides) -> OrgMember:
    defaults = dict(
        id=uuid4(),
        organization_id=uuid4(),
        user_id=uuid4(),
        role="member",
        joined_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return OrgMember(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def member_id():
    return uuid4()


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def sample_org(org_id):
    return _make_org(id=org_id)


@pytest.fixture
def mock_org_repo():
    from app.repositories.organization_repo import OrganizationRepository
    return AsyncMock(spec=OrganizationRepository)


@pytest.fixture
def org_service(mock_org_repo):
    from app.services.organization_service import OrganizationService
    return OrganizationService(repo=mock_org_repo)


@pytest.fixture
def mock_org_service():
    from app.services.organization_service import OrganizationService
    return AsyncMock(spec=OrganizationService)


@pytest.fixture
def fixed_user_id():
    return uuid4()


@pytest.fixture
async def client(mock_org_service, fixed_user_id):
    from app.routes.organization_routes import router, _get_org_service, _get_current_user_id

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)
    app.dependency_overrides[_get_org_service] = lambda: mock_org_service
    app.dependency_overrides[_get_current_user_id] = lambda: fixed_user_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Service unit tests — create_organization
# ---------------------------------------------------------------------------

class TestOrgServiceCreate:
    async def test_create_organization_success(self, org_service, mock_org_repo, owner_id):
        org = _make_org()
        owner_member = _make_member(organization_id=org.id, user_id=owner_id, role="owner")
        mock_org_repo.create.return_value = org
        mock_org_repo.add_member.return_value = owner_member

        result = await org_service.create_organization(name="Acme Corp", slug="acme-corp", owner_user_id=owner_id)

        assert result.name == "Acme Corp"
        mock_org_repo.create.assert_called_once_with(name="Acme Corp", slug="acme-corp", settings={})
        mock_org_repo.add_member.assert_called_once_with(org.id, owner_id, "owner")

    async def test_create_organization_duplicate_slug_conflict(self, org_service, mock_org_repo, owner_id):
        mock_org_repo.create.side_effect = ConflictError("Organization slug already exists")

        with pytest.raises(ConflictError, match="slug already exists"):
            await org_service.create_organization(name="Acme", slug="acme", owner_user_id=owner_id)

    async def test_create_organization_invalid_slug(self, org_service, owner_id):
        with pytest.raises(AppError, match="Invalid slug"):
            await org_service.create_organization(name="Acme", slug="Acme Corp!", owner_user_id=owner_id)

    async def test_create_organization_slug_leading_hyphen(self, org_service, owner_id):
        with pytest.raises(AppError, match="Invalid slug"):
            await org_service.create_organization(name="Acme", slug="-acme", owner_user_id=owner_id)

    async def test_create_organization_slug_trailing_hyphen(self, org_service, owner_id):
        with pytest.raises(AppError, match="Invalid slug"):
            await org_service.create_organization(name="Acme", slug="acme-", owner_user_id=owner_id)

    async def test_create_organization_empty_name(self, org_service, owner_id):
        with pytest.raises(AppError, match="Organization name cannot be empty"):
            await org_service.create_organization(name="", slug="acme", owner_user_id=owner_id)

    async def test_create_organization_name_too_long(self, org_service, owner_id):
        with pytest.raises(AppError, match="Organization name too long"):
            await org_service.create_organization(name="A" * 201, slug="acme", owner_user_id=owner_id)


# ---------------------------------------------------------------------------
# Service unit tests — get_organization
# ---------------------------------------------------------------------------

class TestOrgServiceGet:
    async def test_get_organization_success(self, org_service, mock_org_repo, org_id, sample_org):
        mock_org_repo.get_by_id.return_value = sample_org

        result = await org_service.get_organization(org_id)

        assert result.id == org_id

    async def test_get_organization_not_found(self, org_service, mock_org_repo):
        mock_org_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError, match="Organization not found"):
            await org_service.get_organization(uuid4())


# ---------------------------------------------------------------------------
# Service unit tests — invite_member
# ---------------------------------------------------------------------------

class TestOrgServiceInvite:
    async def test_invite_member_success(self, org_service, mock_org_repo, org_id, owner_id, member_id):
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        new_member = _make_member(organization_id=org_id, user_id=member_id, role="member")
        mock_org_repo.get_member.return_value = owner_member
        mock_org_repo.add_member.return_value = new_member

        result = await org_service.invite_member(org_id, member_id, inviter_user_id=owner_id, role="member")

        assert result.user_id == member_id
        assert result.role == "member"

    async def test_invite_member_by_admin(self, org_service, mock_org_repo, org_id, member_id):
        admin_id = uuid4()
        admin_member = _make_member(organization_id=org_id, user_id=admin_id, role="admin")
        new_member = _make_member(organization_id=org_id, user_id=member_id, role="member")
        mock_org_repo.get_member.return_value = admin_member
        mock_org_repo.add_member.return_value = new_member

        result = await org_service.invite_member(org_id, member_id, inviter_user_id=admin_id, role="member")

        assert result.user_id == member_id

    async def test_invite_member_forbidden_for_regular_member(self, org_service, mock_org_repo, org_id, member_id):
        regular = _make_member(organization_id=org_id, user_id=uuid4(), role="member")
        mock_org_repo.get_member.return_value = regular

        with pytest.raises(ForbiddenError, match="Only owner or admin can invite"):
            await org_service.invite_member(org_id, member_id, inviter_user_id=regular.user_id)

    async def test_invite_member_forbidden_not_a_member(self, org_service, mock_org_repo, org_id, member_id):
        mock_org_repo.get_member.return_value = None

        with pytest.raises(ForbiddenError, match="Only owner or admin can invite"):
            await org_service.invite_member(org_id, member_id, inviter_user_id=uuid4())

    async def test_invite_duplicate_member_conflict(self, org_service, mock_org_repo, org_id, owner_id, member_id):
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        mock_org_repo.get_member.return_value = owner_member
        mock_org_repo.add_member.side_effect = ConflictError("User is already a member")

        with pytest.raises(ConflictError, match="already a member"):
            await org_service.invite_member(org_id, member_id, inviter_user_id=owner_id)

    async def test_invite_member_invalid_role(self, org_service, mock_org_repo, org_id, owner_id, member_id):
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        mock_org_repo.get_member.return_value = owner_member

        with pytest.raises(AppError, match="Invalid role"):
            await org_service.invite_member(org_id, member_id, inviter_user_id=owner_id, role="superadmin")


# ---------------------------------------------------------------------------
# Service unit tests — remove_member
# ---------------------------------------------------------------------------

class TestOrgServiceRemove:
    async def test_remove_member_success(self, org_service, mock_org_repo, org_id, owner_id, member_id):
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        mock_org_repo.get_member.side_effect = [
            owner_member,  # first call: get remover
            _make_member(organization_id=org_id, user_id=member_id, role="member"),  # target
        ]
        mock_org_repo.remove_member.return_value = True

        await org_service.remove_member(org_id, member_id, remover_user_id=owner_id)

        mock_org_repo.remove_member.assert_called_once_with(org_id, member_id)

    async def test_remove_member_forbidden_for_regular(self, org_service, mock_org_repo, org_id, member_id):
        regular = _make_member(organization_id=org_id, user_id=uuid4(), role="member")
        mock_org_repo.get_member.return_value = regular

        with pytest.raises(ForbiddenError, match="Only owner or admin can remove"):
            await org_service.remove_member(org_id, member_id, remover_user_id=regular.user_id)

    async def test_remove_owner_forbidden(self, org_service, mock_org_repo, org_id, owner_id):
        admin_id = uuid4()
        admin_member = _make_member(organization_id=org_id, user_id=admin_id, role="admin")
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        mock_org_repo.get_member.side_effect = [admin_member, owner_member]

        with pytest.raises(ForbiddenError, match="Cannot remove the owner"):
            await org_service.remove_member(org_id, owner_id, remover_user_id=admin_id)

    async def test_remove_nonexistent_member(self, org_service, mock_org_repo, org_id, owner_id, member_id):
        owner_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        mock_org_repo.get_member.side_effect = [owner_member, None]

        with pytest.raises(NotFoundError, match="Member not found"):
            await org_service.remove_member(org_id, member_id, remover_user_id=owner_id)


# ---------------------------------------------------------------------------
# Service unit tests — get_my_organizations
# ---------------------------------------------------------------------------

class TestOrgServiceMyOrgs:
    async def test_get_my_organizations(self, org_service, mock_org_repo, owner_id, sample_org):
        mock_org_repo.get_user_orgs.return_value = [sample_org]

        result = await org_service.get_my_organizations(owner_id)

        assert len(result) == 1
        assert result[0].id == sample_org.id
        mock_org_repo.get_user_orgs.assert_called_once_with(owner_id)

    async def test_get_my_organizations_empty(self, org_service, mock_org_repo, owner_id):
        mock_org_repo.get_user_orgs.return_value = []

        result = await org_service.get_my_organizations(owner_id)

        assert result == []


# ---------------------------------------------------------------------------
# Service unit tests — get_members
# ---------------------------------------------------------------------------

class TestOrgServiceGetMembers:
    async def test_get_members_success(self, org_service, mock_org_repo, org_id, owner_id):
        caller_member = _make_member(organization_id=org_id, user_id=owner_id, role="owner")
        members = [caller_member, _make_member(organization_id=org_id)]
        mock_org_repo.get_member.return_value = caller_member
        mock_org_repo.get_members.return_value = members

        result = await org_service.get_members(org_id, owner_id, limit=20, offset=0)

        assert len(result) == 2

    async def test_get_members_forbidden_non_member(self, org_service, mock_org_repo, org_id):
        mock_org_repo.get_member.return_value = None

        with pytest.raises(ForbiddenError, match="Not a member"):
            await org_service.get_members(org_id, uuid4(), limit=20, offset=0)


# ---------------------------------------------------------------------------
# Route tests — POST /organizations
# ---------------------------------------------------------------------------

class TestOrgRouteCreate:
    async def test_create_org_201(self, client, mock_org_service, fixed_user_id):
        org = _make_org()
        mock_org_service.create_organization.return_value = org

        resp = await client.post("/organizations", json={"name": "Acme Corp", "slug": "acme-corp"})

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Corp"
        mock_org_service.create_organization.assert_called_once_with(
            name="Acme Corp", slug="acme-corp", owner_user_id=fixed_user_id
        )

    async def test_create_org_conflict_409(self, client, mock_org_service):
        mock_org_service.create_organization.side_effect = ConflictError("Organization slug already exists")

        resp = await client.post("/organizations", json={"name": "Acme", "slug": "acme"})

        assert resp.status_code == 409

    async def test_create_org_invalid_slug_400(self, client, mock_org_service):
        mock_org_service.create_organization.side_effect = AppError("Invalid slug")

        resp = await client.post("/organizations", json={"name": "Acme", "slug": "bad slug!"})

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Route tests — GET /organizations/me
# ---------------------------------------------------------------------------

class TestOrgRouteMyOrgs:
    async def test_get_my_orgs_200(self, client, mock_org_service, fixed_user_id):
        org = _make_org()
        mock_org_service.get_my_organizations.return_value = [org]

        resp = await client.get("/organizations/me")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["slug"] == "acme-corp"

    async def test_get_my_orgs_empty(self, client, mock_org_service):
        mock_org_service.get_my_organizations.return_value = []

        resp = await client.get("/organizations/me")

        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Route tests — GET /organizations/{id}
# ---------------------------------------------------------------------------

class TestOrgRouteGetOne:
    async def test_get_org_200(self, client, mock_org_service, fixed_user_id):
        org = _make_org()
        mock_org_service.get_organization_for_member.return_value = org

        resp = await client.get(f"/organizations/{org.id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == str(org.id)

    async def test_get_org_not_found_404(self, client, mock_org_service):
        mock_org_service.get_organization_for_member.side_effect = NotFoundError("Organization not found")

        resp = await client.get(f"/organizations/{uuid4()}")

        assert resp.status_code == 404

    async def test_get_org_forbidden_403(self, client, mock_org_service):
        mock_org_service.get_organization_for_member.side_effect = ForbiddenError("Not a member")

        resp = await client.get(f"/organizations/{uuid4()}")

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Route tests — POST /organizations/{id}/members
# ---------------------------------------------------------------------------

class TestOrgRouteMembersAdd:
    async def test_add_member_201(self, client, mock_org_service, fixed_user_id):
        org_id = uuid4()
        member_id = uuid4()
        member = _make_member(organization_id=org_id, user_id=member_id)
        mock_org_service.invite_member.return_value = member

        resp = await client.post(
            f"/organizations/{org_id}/members",
            json={"user_id": str(member_id), "role": "member"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == str(member_id)

    async def test_add_member_forbidden_403(self, client, mock_org_service):
        org_id = uuid4()
        mock_org_service.invite_member.side_effect = ForbiddenError("Only owner or admin can invite")

        resp = await client.post(
            f"/organizations/{org_id}/members",
            json={"user_id": str(uuid4()), "role": "member"},
        )

        assert resp.status_code == 403

    async def test_add_member_conflict_409(self, client, mock_org_service):
        org_id = uuid4()
        mock_org_service.invite_member.side_effect = ConflictError("User is already a member")

        resp = await client.post(
            f"/organizations/{org_id}/members",
            json={"user_id": str(uuid4()), "role": "member"},
        )

        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Route tests — DELETE /organizations/{id}/members/{user_id}
# ---------------------------------------------------------------------------

class TestOrgRouteMembersRemove:
    async def test_remove_member_204(self, client, mock_org_service, fixed_user_id):
        org_id = uuid4()
        target_id = uuid4()

        resp = await client.delete(f"/organizations/{org_id}/members/{target_id}")

        assert resp.status_code == 204
        mock_org_service.remove_member.assert_called_once_with(
            org_id, target_id, remover_user_id=fixed_user_id
        )

    async def test_remove_member_forbidden_403(self, client, mock_org_service):
        org_id = uuid4()
        mock_org_service.remove_member.side_effect = ForbiddenError("Only owner or admin can remove")

        resp = await client.delete(f"/organizations/{org_id}/members/{uuid4()}")

        assert resp.status_code == 403

    async def test_remove_owner_forbidden_403(self, client, mock_org_service):
        org_id = uuid4()
        mock_org_service.remove_member.side_effect = ForbiddenError("Cannot remove the owner")

        resp = await client.delete(f"/organizations/{org_id}/members/{uuid4()}")

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Route tests — GET /organizations/{id}/members
# ---------------------------------------------------------------------------

class TestOrgRouteMembersList:
    async def test_get_members_200(self, client, mock_org_service, fixed_user_id):
        org_id = uuid4()
        members = [_make_member(organization_id=org_id, user_id=fixed_user_id, role="owner")]
        mock_org_service.get_members.return_value = members

        resp = await client.get(f"/organizations/{org_id}/members")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_get_members_forbidden_403(self, client, mock_org_service):
        org_id = uuid4()
        mock_org_service.get_members.side_effect = ForbiddenError("Not a member")

        resp = await client.get(f"/organizations/{org_id}/members")

        assert resp.status_code == 403
