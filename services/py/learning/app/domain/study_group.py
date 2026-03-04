from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class StudyGroup:
    id: UUID
    course_id: UUID
    name: str
    description: str | None
    creator_id: UUID
    max_members: int
    created_at: datetime


@dataclass(frozen=True)
class GroupMember:
    id: UUID
    group_id: UUID
    user_id: UUID
    joined_at: datetime


@dataclass(frozen=True)
class StudyGroupWithCount:
    group: StudyGroup
    member_count: int


class CreateStudyGroupRequest(BaseModel):
    course_id: UUID
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class StudyGroupResponse(BaseModel):
    id: UUID
    course_id: UUID
    name: str
    description: str | None
    creator_id: UUID
    max_members: int
    created_at: datetime


class StudyGroupWithCountResponse(BaseModel):
    id: UUID
    course_id: UUID
    name: str
    description: str | None
    creator_id: UUID
    max_members: int
    created_at: datetime
    member_count: int


class GroupMemberResponse(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    joined_at: datetime


class StudyGroupListResponse(BaseModel):
    groups: list[StudyGroupWithCountResponse]
    total: int


class MemberListResponse(BaseModel):
    members: list[GroupMemberResponse]
    total: int
