import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone

from common.errors import ConflictError, ForbiddenError
from app.domain.enrollment import Enrollment, EnrollmentStatus
from app.domain.progress import LessonProgress
from app.services.progress_service import ProgressService


@pytest.mark.asyncio
async def test_complete_lesson(progress_service: ProgressService, mock_progress_repo: AsyncMock, mock_repo: AsyncMock, sample_progress: LessonProgress, sample_enrollment, student_id, lesson_id, course_id):
    mock_progress_repo.complete_lesson.return_value = sample_progress
    mock_repo.get_by_student_and_course.return_value = sample_enrollment
    mock_progress_repo.count_completed.return_value = 1

    result = await progress_service.complete_lesson(
        student_id=student_id, role="student",
        lesson_id=lesson_id, course_id=course_id,
    )

    assert result.lesson_id == lesson_id
    mock_progress_repo.complete_lesson.assert_called_once()


@pytest.mark.asyncio
async def test_complete_lesson_duplicate(progress_service: ProgressService, mock_progress_repo: AsyncMock, student_id, lesson_id, course_id):
    mock_progress_repo.complete_lesson.side_effect = ConflictError("Lesson already completed")

    with pytest.raises(ConflictError, match="already completed"):
        await progress_service.complete_lesson(
            student_id=student_id, role="student",
            lesson_id=lesson_id, course_id=course_id,
        )


@pytest.mark.asyncio
async def test_complete_lesson_teacher_forbidden(progress_service: ProgressService):
    with pytest.raises(ForbiddenError, match="Only students"):
        await progress_service.complete_lesson(
            student_id=uuid4(), role="teacher",
            lesson_id=uuid4(), course_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_get_course_progress(progress_service: ProgressService, mock_progress_repo: AsyncMock, student_id, course_id):
    mock_progress_repo.count_completed.return_value = 3

    result = await progress_service.get_course_progress(
        student_id=student_id, course_id=course_id, total_lessons=10,
    )

    assert result["completed_lessons"] == 3
    assert result["total_lessons"] == 10
    assert result["percentage"] == 30.0


@pytest.mark.asyncio
async def test_list_completed_lessons(progress_service: ProgressService, mock_progress_repo: AsyncMock, student_id, course_id, lesson_id):
    mock_progress_repo.list_completed_lessons.return_value = [lesson_id]

    result = await progress_service.list_completed_lessons(student_id, course_id)

    assert len(result) == 1
    assert result[0] == lesson_id


@pytest.mark.asyncio
async def test_auto_complete_on_last_lesson(mock_progress_repo: AsyncMock, mock_repo: AsyncMock, student_id, lesson_id, course_id, enrollment_id):
    enrollment = Enrollment(
        id=enrollment_id, student_id=student_id, course_id=course_id,
        payment_id=None, status=EnrollmentStatus.IN_PROGRESS,
        enrolled_at=datetime.now(timezone.utc), total_lessons=3,
    )
    progress = LessonProgress(
        id=uuid4(), student_id=student_id, lesson_id=lesson_id,
        course_id=course_id, completed_at=datetime.now(timezone.utc),
    )
    mock_progress_repo.complete_lesson.return_value = progress
    mock_repo.get_by_student_and_course.return_value = enrollment
    mock_progress_repo.count_completed.return_value = 3

    service = ProgressService(repo=mock_progress_repo, enrollment_repo=mock_repo)
    await service.complete_lesson(student_id, "student", lesson_id, course_id)

    mock_repo.update_status.assert_called_once_with(enrollment_id, EnrollmentStatus.COMPLETED)


@pytest.mark.asyncio
async def test_auto_in_progress_on_first_lesson(mock_progress_repo: AsyncMock, mock_repo: AsyncMock, student_id, lesson_id, course_id, enrollment_id):
    enrollment = Enrollment(
        id=enrollment_id, student_id=student_id, course_id=course_id,
        payment_id=None, status=EnrollmentStatus.ENROLLED,
        enrolled_at=datetime.now(timezone.utc), total_lessons=5,
    )
    progress = LessonProgress(
        id=uuid4(), student_id=student_id, lesson_id=lesson_id,
        course_id=course_id, completed_at=datetime.now(timezone.utc),
    )
    mock_progress_repo.complete_lesson.return_value = progress
    mock_repo.get_by_student_and_course.return_value = enrollment
    mock_progress_repo.count_completed.return_value = 1

    service = ProgressService(repo=mock_progress_repo, enrollment_repo=mock_repo)
    await service.complete_lesson(student_id, "student", lesson_id, course_id)

    mock_repo.update_status.assert_called_once_with(enrollment_id, EnrollmentStatus.IN_PROGRESS)


@pytest.mark.asyncio
async def test_no_status_change_when_total_lessons_zero(mock_progress_repo: AsyncMock, mock_repo: AsyncMock, student_id, lesson_id, course_id, enrollment_id):
    enrollment = Enrollment(
        id=enrollment_id, student_id=student_id, course_id=course_id,
        payment_id=None, status=EnrollmentStatus.ENROLLED,
        enrolled_at=datetime.now(timezone.utc), total_lessons=0,
    )
    progress = LessonProgress(
        id=uuid4(), student_id=student_id, lesson_id=lesson_id,
        course_id=course_id, completed_at=datetime.now(timezone.utc),
    )
    mock_progress_repo.complete_lesson.return_value = progress
    mock_repo.get_by_student_and_course.return_value = enrollment

    service = ProgressService(repo=mock_progress_repo, enrollment_repo=mock_repo)
    await service.complete_lesson(student_id, "student", lesson_id, course_id)

    mock_repo.update_status.assert_not_called()
