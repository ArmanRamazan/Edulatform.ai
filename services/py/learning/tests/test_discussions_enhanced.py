from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.domain.discussion import Comment, ThreadedComment
from app.repositories.discussion_repo import DiscussionRepository
from app.services.discussion_service import DiscussionService
from common.errors import ForbiddenError, NotFoundError, AppError


def _make_comment(
    user_id=None,
    lesson_id=None,
    course_id=None,
    parent_id=None,
    upvote_count=0,
    content="Great lesson!",
    comment_id=None,
    is_pinned=False,
    is_teacher_answer=False,
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
        is_pinned=is_pinned,
        is_teacher_answer=is_teacher_answer,
    )


@pytest.fixture
def mock_discussion_repo():
    return AsyncMock(spec=DiscussionRepository)


@pytest.fixture
def discussion_service(mock_discussion_repo):
    return DiscussionService(repo=mock_discussion_repo)


class TestCreateReply:
    async def test_create_reply_success(
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

        result = await discussion_service.create_reply(
            user_id=user_id,
            comment_id=parent_id,
            content="Thanks for the explanation!",
        )

        assert result.parent_id == parent_id
        assert result.lesson_id == lesson_id
        mock_discussion_repo.create_comment.assert_awaited_once_with(
            lesson_id=lesson_id,
            course_id=course_id,
            user_id=user_id,
            content="Thanks for the explanation!",
            parent_id=parent_id,
        )

    async def test_create_reply_max_depth_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        """Reply to a reply (parent already has parent_id) should raise error."""
        grandparent_id = uuid4()
        parent_id = uuid4()
        parent = _make_comment(
            comment_id=parent_id, parent_id=grandparent_id,
        )
        mock_discussion_repo.get_comment_by_id.return_value = parent

        with pytest.raises(AppError, match="Maximum reply depth"):
            await discussion_service.create_reply(
                user_id=uuid4(),
                comment_id=parent_id,
                content="Too deep!",
            )

    async def test_create_reply_parent_not_found(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.create_reply(
                user_id=uuid4(),
                comment_id=uuid4(),
                content="Reply to nothing",
            )


class TestPinDiscussion:
    async def test_pin_discussion_teacher(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment(is_pinned=False)
        pinned = _make_comment(
            comment_id=comment.id, is_pinned=True,
        )
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.set_pinned.return_value = pinned

        result = await discussion_service.pin_comment(
            user_id=uuid4(), comment_id=comment.id, role="teacher",
        )

        assert result.is_pinned is True
        mock_discussion_repo.set_pinned.assert_awaited_once_with(
            comment.id, True,
        )

    async def test_pin_discussion_student_forbidden(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment()
        mock_discussion_repo.get_comment_by_id.return_value = comment

        with pytest.raises(ForbiddenError):
            await discussion_service.pin_comment(
                user_id=uuid4(), comment_id=comment.id, role="student",
            )

    async def test_unpin_discussion_teacher(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment(is_pinned=True)
        unpinned = _make_comment(comment_id=comment.id, is_pinned=False)
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.set_pinned.return_value = unpinned

        result = await discussion_service.pin_comment(
            user_id=uuid4(), comment_id=comment.id, role="teacher",
        )

        assert result.is_pinned is False
        mock_discussion_repo.set_pinned.assert_awaited_once_with(
            comment.id, False,
        )

    async def test_pin_nonexistent_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.pin_comment(
                user_id=uuid4(), comment_id=uuid4(), role="teacher",
            )


class TestMarkTeacherAnswer:
    async def test_mark_answer_teacher(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment(is_teacher_answer=False)
        marked = _make_comment(
            comment_id=comment.id, is_teacher_answer=True,
        )
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.set_teacher_answer.return_value = marked

        result = await discussion_service.mark_teacher_answer(
            user_id=uuid4(), comment_id=comment.id, role="teacher",
        )

        assert result.is_teacher_answer is True
        mock_discussion_repo.set_teacher_answer.assert_awaited_once_with(
            comment.id, True,
        )

    async def test_mark_answer_student_forbidden(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment()
        mock_discussion_repo.get_comment_by_id.return_value = comment

        with pytest.raises(ForbiddenError):
            await discussion_service.mark_teacher_answer(
                user_id=uuid4(), comment_id=comment.id, role="student",
            )

    async def test_unmark_answer_teacher(
        self, discussion_service, mock_discussion_repo,
    ):
        comment = _make_comment(is_teacher_answer=True)
        unmarked = _make_comment(comment_id=comment.id, is_teacher_answer=False)
        mock_discussion_repo.get_comment_by_id.return_value = comment
        mock_discussion_repo.set_teacher_answer.return_value = unmarked

        result = await discussion_service.mark_teacher_answer(
            user_id=uuid4(), comment_id=comment.id, role="teacher",
        )

        assert result.is_teacher_answer is False
        mock_discussion_repo.set_teacher_answer.assert_awaited_once_with(
            comment.id, False,
        )

    async def test_mark_nonexistent_raises(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_comment_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await discussion_service.mark_teacher_answer(
                user_id=uuid4(), comment_id=uuid4(), role="teacher",
            )


class TestGetThreadedDiscussions:
    async def test_returns_threaded_structure(
        self, discussion_service, mock_discussion_repo,
    ):
        lesson_id = uuid4()
        parent = _make_comment(lesson_id=lesson_id)
        reply = _make_comment(
            lesson_id=lesson_id, parent_id=parent.id,
        )
        threaded = [
            ThreadedComment(comment=parent, replies=[reply]),
        ]
        mock_discussion_repo.get_threaded_comments.return_value = (threaded, 1)

        result = await discussion_service.list_threaded_comments(
            lesson_id=lesson_id,
        )

        assert len(result.threads) == 1
        assert result.threads[0].comment.id == parent.id
        assert len(result.threads[0].replies) == 1
        assert result.threads[0].replies[0].id == reply.id
        assert result.total == 1

    async def test_threaded_order_pinned_first(
        self, discussion_service, mock_discussion_repo,
    ):
        lesson_id = uuid4()
        regular = _make_comment(lesson_id=lesson_id)
        pinned = _make_comment(lesson_id=lesson_id, is_pinned=True)
        teacher_answer = _make_comment(
            lesson_id=lesson_id, is_teacher_answer=True,
        )
        threaded = [
            ThreadedComment(comment=pinned, replies=[]),
            ThreadedComment(comment=teacher_answer, replies=[]),
            ThreadedComment(comment=regular, replies=[]),
        ]
        mock_discussion_repo.get_threaded_comments.return_value = (threaded, 3)

        result = await discussion_service.list_threaded_comments(
            lesson_id=lesson_id,
        )

        assert result.threads[0].comment.is_pinned is True
        assert result.threads[1].comment.is_teacher_answer is True
        assert result.total == 3

    async def test_threaded_empty(
        self, discussion_service, mock_discussion_repo,
    ):
        mock_discussion_repo.get_threaded_comments.return_value = ([], 0)

        result = await discussion_service.list_threaded_comments(
            lesson_id=uuid4(),
        )

        assert result.threads == []
        assert result.total == 0
