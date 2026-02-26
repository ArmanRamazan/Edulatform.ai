from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.discussion import Comment
from app.repositories.discussion_repo import DiscussionRepository
from app.services.discussion_service import DiscussionService
from common.errors import ForbiddenError, NotFoundError


def _make_comment(
    user_id=None,
    lesson_id=None,
    course_id=None,
    parent_id=None,
    upvote_count=0,
    content="Great lesson!",
    comment_id=None,
) -> Comment:
    now = datetime.now(timezone.utc)
    return Comment(
        id=comment_id or uuid4(),
        lesson_id=lesson_id or uuid4(),
        course_id=course_id or uuid4(),
        user_id=user_id or uuid4(),
        content=content,
        parent_id=parent_id,
        upvote_count=upvote_count,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_discussion_repo():
    return AsyncMock(spec=DiscussionRepository)


@pytest.fixture
def discussion_service(mock_discussion_repo):
    return DiscussionService(repo=mock_discussion_repo)


class TestCreateComment:
    async def test_creates_top_level_comment(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        lesson_id = uuid4()
        course_id = uuid4()
        comment = _make_comment(
            user_id=user_id, lesson_id=lesson_id, course_id=course_id,
        )
        mock_discussion_repo.create_comment.return_value = comment

        result = await discussion_service.create_comment(
            lesson_id=lesson_id,
            course_id=course_id,
            user_id=user_id,
            content="Great lesson!",
        )

        assert result.lesson_id == lesson_id
        assert result.user_id == user_id
        mock_discussion_repo.create_comment.assert_awaited_once_with(
            lesson_id=lesson_id,
            course_id=course_id,
            user_id=user_id,
            content="Great lesson!",
            parent_id=None,
        )

    async def test_creates_reply_to_existing_comment(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        lesson_id = uuid4()
        course_id = uuid4()
        parent_id = uuid4()
        parent = _make_comment(
            comment_id=parent_id, lesson_id=lesson_id, course_id=course_id,
        )
        reply = _make_comment(
            user_id=user_id,
            lesson_id=lesson_id,
            course_id=course_id,
            parent_id=parent_id,
        )
        mock_discussion_repo.get_comment_by_id.return_value = parent
        mock_discussion_repo.create_comment.return_value = reply

        result = await discussion_service.create_comment(
            lesson_id=lesson_id,
            course_id=course_id,
            user_id=user_id,
            content="Great lesson!",
            parent_id=parent_id,
        )

        assert result.parent_id == parent_id

    async def test_reply_to_nonexistent_comment_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.create_comment(
                lesson_id=uuid4(),
                course_id=uuid4(),
                user_id=uuid4(),
                content="Reply",
                parent_id=uuid4(),
            )


class TestListComments:
    async def test_returns_comments_with_total(
        self, discussion_service, mock_discussion_repo,
    ):
        lesson_id = uuid4()
        comments = [_make_comment(lesson_id=lesson_id) for _ in range(3)]
        mock_discussion_repo.list_comments.return_value = (comments, 3)

        result = await discussion_service.list_comments(lesson_id)

        assert len(result.comments) == 3
        assert result.total == 3
        mock_discussion_repo.list_comments.assert_awaited_once_with(
            lesson_id=lesson_id, limit=20, offset=0,
        )

    async def test_returns_empty_list(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.list_comments.return_value = ([], 0)

        result = await discussion_service.list_comments(uuid4())

        assert result.comments == []
        assert result.total == 0


class TestUpdateComment:
    async def test_owner_can_update(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        comment = _make_comment(user_id=user_id, content="Old")
        updated = _make_comment(
            comment_id=comment.id, user_id=user_id, content="New",
        )
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.update_comment.return_value = updated

        result = await discussion_service.update_comment(
            comment_id=comment.id, user_id=user_id, content="New",
        )

        assert result.content == "New"

    async def test_non_owner_cannot_update(
        self, discussion_service, mock_discussion_repo,
    ):
        owner_id = uuid4()
        other_id = uuid4()
        comment = _make_comment(user_id=owner_id)
        mock_discussion_repo.get_comment_by_id.return_value = comment

        with pytest.raises(ForbiddenError):
            await discussion_service.update_comment(
                comment_id=comment.id, user_id=other_id, content="Hack",
            )

    async def test_update_nonexistent_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.update_comment(
                comment_id=uuid4(), user_id=uuid4(), content="X",
            )


class TestDeleteComment:
    async def test_owner_can_delete(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        comment = _make_comment(user_id=user_id)
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.delete_comment.return_value = True

        await discussion_service.delete_comment(comment.id, user_id)

        mock_discussion_repo.delete_comment.assert_awaited_once_with(comment.id)

    async def test_non_owner_cannot_delete(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment(user_id=uuid4())
        mock_discussion_repo.get_comment_by_id.return_value = comment

        with pytest.raises(ForbiddenError):
            await discussion_service.delete_comment(comment.id, uuid4())

    async def test_delete_nonexistent_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.delete_comment(uuid4(), uuid4())


class TestToggleUpvote:
    async def test_upvote_new(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        comment = _make_comment(upvote_count=0)
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.has_voted.return_value = False
        mock_discussion_repo.add_vote.return_value = True
        updated = _make_comment(
            comment_id=comment.id, upvote_count=1,
        )
        mock_discussion_repo.get_comment_by_id.side_effect = [comment, updated]

        result = await discussion_service.toggle_upvote(comment.id, user_id)

        assert result.upvoted is True
        assert result.upvote_count == 1
        mock_discussion_repo.add_vote.assert_awaited_once()

    async def test_remove_existing_upvote(
        self, discussion_service, mock_discussion_repo,
    ):
        user_id = uuid4()
        comment = _make_comment(upvote_count=1)
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.has_voted.return_value = True
        mock_discussion_repo.remove_vote.return_value = True
        updated = _make_comment(
            comment_id=comment.id, upvote_count=0,
        )
        mock_discussion_repo.get_comment_by_id.side_effect = [comment, updated]

        result = await discussion_service.toggle_upvote(comment.id, user_id)

        assert result.upvoted is False
        assert result.upvote_count == 0
        mock_discussion_repo.remove_vote.assert_awaited_once()

    async def test_upvote_nonexistent_comment_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.toggle_upvote(uuid4(), uuid4())
