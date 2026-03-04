from __future__ import annotations

from uuid import UUID

from common.errors import AppError, ConflictError, NotFoundError
from app.domain.study_group import (
    GroupMember,
    MemberListResponse,
    GroupMemberResponse,
    StudyGroup,
    StudyGroupListResponse,
    StudyGroupWithCountResponse,
)
from app.repositories.study_group_repo import StudyGroupRepository


class StudyGroupService:
    def __init__(self, repo: StudyGroupRepository) -> None:
        self._repo = repo

    async def create_group(
        self, user_id: UUID, course_id: UUID, name: str, description: str | None = None,
    ) -> StudyGroup:
        if not name or len(name) > 100:
            raise AppError("Group name must be 1-100 characters", status_code=422)

        group = await self._repo.create_group(
            course_id=course_id,
            name=name,
            description=description,
            creator_id=user_id,
            max_members=10,
        )
        await self._repo.add_member(group.id, user_id)
        return group

    async def get_course_groups(
        self, course_id: UUID, limit: int = 20, offset: int = 0,
    ) -> StudyGroupListResponse:
        groups_with_count, total = await self._repo.get_course_groups(course_id, limit, offset)
        return StudyGroupListResponse(
            groups=[
                StudyGroupWithCountResponse(
                    id=gwc.group.id,
                    course_id=gwc.group.course_id,
                    name=gwc.group.name,
                    description=gwc.group.description,
                    creator_id=gwc.group.creator_id,
                    max_members=gwc.group.max_members,
                    created_at=gwc.group.created_at,
                    member_count=gwc.member_count,
                )
                for gwc in groups_with_count
            ],
            total=total,
        )

    async def join_group(self, user_id: UUID, group_id: UUID) -> GroupMember:
        group = await self._repo.get_group(group_id)
        if group is None:
            raise NotFoundError("Study group not found")

        if await self._repo.is_member(group_id, user_id):
            raise ConflictError("Already a member of this group")

        count = await self._repo.count_members(group_id)
        if count >= group.max_members:
            raise AppError("Study group is full", status_code=400)

        return await self._repo.add_member(group_id, user_id)

    async def leave_group(self, user_id: UUID, group_id: UUID) -> None:
        group = await self._repo.get_group(group_id)
        if group is None:
            raise NotFoundError("Study group not found")

        if not await self._repo.is_member(group_id, user_id):
            raise NotFoundError("Not a member of this group")

        if group.creator_id == user_id:
            raise AppError("Group creator cannot leave the group", status_code=400)

        await self._repo.remove_member(group_id, user_id)

    async def get_members(
        self, group_id: UUID, limit: int = 20, offset: int = 0,
    ) -> MemberListResponse:
        members, total = await self._repo.get_members(group_id, limit, offset)
        return MemberListResponse(
            members=[
                GroupMemberResponse(
                    id=m.id, group_id=m.group_id, user_id=m.user_id, joined_at=m.joined_at,
                )
                for m in members
            ],
            total=total,
        )

    async def get_my_groups(self, user_id: UUID) -> list[StudyGroup]:
        return await self._repo.get_user_groups(user_id)
