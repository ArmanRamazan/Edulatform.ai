from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from common.errors import AppError, ConflictError, NotFoundError
from app.domain.study_group import (
    GroupMember,
    StudyGroup,
    StudyGroupWithCount,
)
from app.repositories.study_group_repo import StudyGroupRepository
from app.services.study_group_service import StudyGroupService


@pytest.fixture
def sg_user_id():
    return uuid4()


@pytest.fixture
def sg_course_id():
    return uuid4()


@pytest.fixture
def sg_group_id():
    return uuid4()


@pytest.fixture
def mock_sg_repo():
    return AsyncMock(spec=StudyGroupRepository)


@pytest.fixture
def sg_service(mock_sg_repo):
    return StudyGroupService(repo=mock_sg_repo)


@pytest.fixture
def sample_group(sg_group_id, sg_course_id, sg_user_id):
    return StudyGroup(
        id=sg_group_id,
        course_id=sg_course_id,
        name="Study Buddies",
        description="Let's learn together",
        creator_id=sg_user_id,
        max_members=10,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_member(sg_group_id, sg_user_id):
    return GroupMember(
        id=uuid4(),
        group_id=sg_group_id,
        user_id=sg_user_id,
        joined_at=datetime.now(timezone.utc),
    )


class TestCreateGroup:
    async def test_create_group_success(
        self, sg_service, mock_sg_repo, sample_group, sample_member, sg_user_id, sg_course_id,
    ):
        mock_sg_repo.create_group.return_value = sample_group
        mock_sg_repo.add_member.return_value = sample_member

        result = await sg_service.create_group(
            user_id=sg_user_id,
            course_id=sg_course_id,
            name="Study Buddies",
            description="Let's learn together",
        )

        assert result == sample_group
        mock_sg_repo.create_group.assert_awaited_once()
        mock_sg_repo.add_member.assert_awaited_once_with(sample_group.id, sg_user_id)

    async def test_create_group_name_too_long(self, sg_service, sg_user_id, sg_course_id):
        with pytest.raises(AppError):
            await sg_service.create_group(
                user_id=sg_user_id,
                course_id=sg_course_id,
                name="x" * 101,
            )

    async def test_create_group_empty_name(self, sg_service, sg_user_id, sg_course_id):
        with pytest.raises(AppError):
            await sg_service.create_group(
                user_id=sg_user_id,
                course_id=sg_course_id,
                name="",
            )


class TestGetCourseGroups:
    async def test_get_course_groups(self, sg_service, mock_sg_repo, sample_group, sg_course_id):
        groups_with_count = [StudyGroupWithCount(group=sample_group, member_count=3)]
        mock_sg_repo.get_course_groups.return_value = (groups_with_count, 1)

        result = await sg_service.get_course_groups(sg_course_id, limit=20, offset=0)

        assert result.total == 1
        assert len(result.groups) == 1
        assert result.groups[0].member_count == 3
        mock_sg_repo.get_course_groups.assert_awaited_once_with(sg_course_id, 20, 0)


class TestJoinGroup:
    async def test_join_group_success(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id,
    ):
        other_user = uuid4()
        expected_member = GroupMember(
            id=uuid4(), group_id=sg_group_id, user_id=other_user,
            joined_at=datetime.now(timezone.utc),
        )
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = False
        mock_sg_repo.count_members.return_value = 3
        mock_sg_repo.add_member.return_value = expected_member

        result = await sg_service.join_group(user_id=other_user, group_id=sg_group_id)

        assert result == expected_member
        mock_sg_repo.add_member.assert_awaited_once_with(sg_group_id, other_user)

    async def test_join_group_not_found(self, sg_service, mock_sg_repo, sg_group_id):
        mock_sg_repo.get_group.return_value = None

        with pytest.raises(NotFoundError):
            await sg_service.join_group(user_id=uuid4(), group_id=sg_group_id)

    async def test_join_group_already_member(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id,
    ):
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = True

        with pytest.raises(ConflictError):
            await sg_service.join_group(user_id=uuid4(), group_id=sg_group_id)

    async def test_join_group_full(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id,
    ):
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = False
        mock_sg_repo.count_members.return_value = 10  # max_members is 10

        with pytest.raises(AppError, match="full"):
            await sg_service.join_group(user_id=uuid4(), group_id=sg_group_id)


class TestLeaveGroup:
    async def test_leave_group_success(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id,
    ):
        other_user = uuid4()
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = True
        mock_sg_repo.remove_member.return_value = True

        await sg_service.leave_group(user_id=other_user, group_id=sg_group_id)

        mock_sg_repo.remove_member.assert_awaited_once_with(sg_group_id, other_user)

    async def test_leave_group_creator_forbidden(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id, sg_user_id,
    ):
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = True

        with pytest.raises(AppError, match="creator"):
            await sg_service.leave_group(user_id=sg_user_id, group_id=sg_group_id)

    async def test_leave_group_not_member(
        self, sg_service, mock_sg_repo, sample_group, sg_group_id,
    ):
        mock_sg_repo.get_group.return_value = sample_group
        mock_sg_repo.is_member.return_value = False

        with pytest.raises(NotFoundError):
            await sg_service.leave_group(user_id=uuid4(), group_id=sg_group_id)

    async def test_leave_group_not_found(self, sg_service, mock_sg_repo, sg_group_id):
        mock_sg_repo.get_group.return_value = None

        with pytest.raises(NotFoundError):
            await sg_service.leave_group(user_id=uuid4(), group_id=sg_group_id)


class TestGetMembers:
    async def test_get_members_paginated(
        self, sg_service, mock_sg_repo, sample_member, sg_group_id,
    ):
        mock_sg_repo.get_members.return_value = ([sample_member], 1)

        result = await sg_service.get_members(sg_group_id, limit=20, offset=0)

        assert result.total == 1
        assert len(result.members) == 1
        mock_sg_repo.get_members.assert_awaited_once_with(sg_group_id, 20, 0)


class TestGetMyGroups:
    async def test_get_my_groups(
        self, sg_service, mock_sg_repo, sample_group, sg_user_id,
    ):
        mock_sg_repo.get_user_groups.return_value = [sample_group]

        result = await sg_service.get_my_groups(user_id=sg_user_id)

        assert len(result) == 1
        assert result[0] == sample_group
        mock_sg_repo.get_user_groups.assert_awaited_once_with(sg_user_id)
