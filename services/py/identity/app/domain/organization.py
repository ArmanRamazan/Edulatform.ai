from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


@dataclass(frozen=True)
class Organization:
    id: UUID
    name: str
    slug: str
    logo_url: str | None
    settings: dict
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class OrgMember:
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None
    settings: dict
    is_active: bool
    created_at: datetime


class OrgMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime


class OrgMemberCreate(BaseModel):
    user_id: UUID
    role: str = "member"


class PaginatedOrgMembersResponse(BaseModel):
    items: list[OrgMemberResponse]
    total: int
