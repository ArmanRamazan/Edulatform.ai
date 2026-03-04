from __future__ import annotations

from uuid import UUID

from common.errors import ForbiddenError
from app.domain.enrollment import EnrollmentStatus
from app.domain.progress import LessonProgress
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository


class ProgressService:
    def __init__(
        self,
        repo: ProgressRepository,
        enrollment_repo: EnrollmentRepository | None = None,
    ) -> None:
        self._repo = repo
        self._enrollment_repo = enrollment_repo

    async def complete_lesson(
        self, student_id: UUID, role: str, lesson_id: UUID, course_id: UUID
    ) -> LessonProgress:
        if role != "student":
            raise ForbiddenError("Only students can complete lessons")
        progress = await self._repo.complete_lesson(student_id, lesson_id, course_id)

        if self._enrollment_repo:
            await self._check_auto_completion(student_id, course_id)

        return progress

    async def _check_auto_completion(self, student_id: UUID, course_id: UUID) -> None:
        assert self._enrollment_repo is not None
        enrollment = await self._enrollment_repo.get_by_student_and_course(student_id, course_id)
        if not enrollment or enrollment.total_lessons == 0:
            return

        completed = await self._repo.count_completed(student_id, course_id)

        if completed >= enrollment.total_lessons and enrollment.status != EnrollmentStatus.COMPLETED:
            await self._enrollment_repo.update_status(enrollment.id, EnrollmentStatus.COMPLETED)
        elif completed == 1 and enrollment.status == EnrollmentStatus.ENROLLED:
            await self._enrollment_repo.update_status(enrollment.id, EnrollmentStatus.IN_PROGRESS)

    async def get_course_progress(
        self, student_id: UUID, course_id: UUID, total_lessons: int
    ) -> dict:
        completed = await self._repo.count_completed(student_id, course_id)
        percentage = (completed / total_lessons * 100) if total_lessons > 0 else 0.0
        return {
            "course_id": course_id,
            "completed_lessons": completed,
            "total_lessons": total_lessons,
            "percentage": round(percentage, 1),
        }

    async def list_completed_lessons(
        self, student_id: UUID, course_id: UUID
    ) -> list[UUID]:
        return await self._repo.list_completed_lessons(student_id, course_id)
