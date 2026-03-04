from __future__ import annotations

from uuid import UUID

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.discussion import (
    CommentListResponse,
    CommentResponse,
    ThreadedCommentResponse,
    ThreadedListResponse,
    UpvoteResponse,
)
from app.repositories.discussion_repo import DiscussionRepository


class DiscussionService:
    def __init__(self, repo: DiscussionRepository) -> None:
        self._repo = repo

    async def create_comment(
        self,
        lesson_id: UUID,
        course_id: UUID,
        user_id: UUID,
        content: str,
        parent_id: UUID | None = None,
    ) -> CommentResponse:
        if parent_id is not None:
            parent = await self._repo.get_comment_by_id(parent_id)
            if parent is None:
                raise NotFoundError("Parent comment not found")

        comment = await self._repo.create_comment(
            lesson_id=lesson_id,
            course_id=course_id,
            user_id=user_id,
            content=content,
            parent_id=parent_id,
        )
        return self._to_response(comment)

    async def list_comments(
        self, lesson_id: UUID, limit: int = 20, offset: int = 0,
    ) -> CommentListResponse:
        comments, total = await self._repo.list_comments(
            lesson_id=lesson_id, limit=limit, offset=offset,
        )
        return CommentListResponse(
            comments=[self._to_response(c) for c in comments],
            total=total,
        )

    async def update_comment(
        self, comment_id: UUID, user_id: UUID, content: str,
    ) -> CommentResponse:
        comment = await self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        if comment.user_id != user_id:
            raise ForbiddenError("Cannot edit another user's comment")

        updated = await self._repo.update_comment(comment_id, content)
        return self._to_response(updated)

    async def delete_comment(self, comment_id: UUID, user_id: UUID) -> None:
        comment = await self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        if comment.user_id != user_id:
            raise ForbiddenError("Cannot delete another user's comment")

        await self._repo.delete_comment(comment_id)

    async def toggle_upvote(
        self, comment_id: UUID, user_id: UUID,
    ) -> UpvoteResponse:
        comment = await self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")

        already_voted = await self._repo.has_voted(comment_id, user_id)

        if already_voted:
            await self._repo.remove_vote(comment_id, user_id)
            upvoted = False
        else:
            await self._repo.add_vote(comment_id, user_id)
            upvoted = True

        refreshed = await self._repo.get_comment_by_id(comment_id)
        return UpvoteResponse(
            comment_id=comment_id,
            upvoted=upvoted,
            upvote_count=refreshed.upvote_count,
        )

    async def create_reply(
        self, user_id: UUID, comment_id: UUID, content: str,
    ) -> CommentResponse:
        parent = await self._repo.get_comment_by_id(comment_id)
        if parent is None:
            raise NotFoundError("Comment not found")
        if parent.parent_id is not None:
            raise AppError("Maximum reply depth exceeded (2 levels)")

        comment = await self._repo.create_comment(
            lesson_id=parent.lesson_id,
            course_id=parent.course_id,
            user_id=user_id,
            content=content,
            parent_id=comment_id,
        )
        return self._to_response(comment)

    async def pin_comment(
        self, user_id: UUID, comment_id: UUID, role: str,
    ) -> CommentResponse:
        comment = await self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        if role != "teacher":
            raise ForbiddenError("Only teachers can pin comments")

        updated = await self._repo.set_pinned(comment_id, not comment.is_pinned)
        return self._to_response(updated)

    async def mark_teacher_answer(
        self, user_id: UUID, comment_id: UUID, role: str,
    ) -> CommentResponse:
        comment = await self._repo.get_comment_by_id(comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        if role != "teacher":
            raise ForbiddenError("Only teachers can mark teacher answers")

        updated = await self._repo.set_teacher_answer(
            comment_id, not comment.is_teacher_answer,
        )
        return self._to_response(updated)

    async def list_threaded_comments(
        self, lesson_id: UUID, limit: int = 20, offset: int = 0,
    ) -> ThreadedListResponse:
        threads, total = await self._repo.get_threaded_comments(
            lesson_id=lesson_id, limit=limit, offset=offset,
        )
        return ThreadedListResponse(
            threads=[
                ThreadedCommentResponse(
                    comment=self._to_response(t.comment),
                    replies=[self._to_response(r) for r in t.replies],
                )
                for t in threads
            ],
            total=total,
        )

    @staticmethod
    def _to_response(comment) -> CommentResponse:
        return CommentResponse(
            id=comment.id,
            lesson_id=comment.lesson_id,
            course_id=comment.course_id,
            user_id=comment.user_id,
            content=comment.content,
            parent_id=comment.parent_id,
            upvote_count=comment.upvote_count,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            is_pinned=comment.is_pinned,
            is_teacher_answer=comment.is_teacher_answer,
        )
