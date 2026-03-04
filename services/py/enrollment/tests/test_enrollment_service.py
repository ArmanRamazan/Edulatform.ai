import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import ConflictError, ForbiddenError
from app.domain.enrollment import Enrollment
from app.services.enrollment_service import EnrollmentService


@pytest.mark.asyncio
async def test_enroll_success(
    enrollment_service: EnrollmentService,
    mock_repo: AsyncMock,
    sample_enrollment: Enrollment,
    student_id,
    course_id,
):
    mock_repo.create.return_value = sample_enrollment

    result = await enrollment_service.enroll(
        student_id=student_id,
        role="student",
        course_id=course_id,
        payment_id=None,
    )

    assert result.id == sample_enrollment.id
    assert result.student_id == student_id
    mock_repo.create.assert_called_once_with(student_id, course_id, None, 0)


@pytest.mark.asyncio
async def test_enroll_with_payment(
    enrollment_service: EnrollmentService,
    mock_repo: AsyncMock,
    sample_enrollment: Enrollment,
    student_id,
    course_id,
):
    payment_id = uuid4()
    mock_repo.create.return_value = sample_enrollment

    await enrollment_service.enroll(
        student_id=student_id,
        role="student",
        course_id=course_id,
        payment_id=payment_id,
    )

    mock_repo.create.assert_called_once_with(student_id, course_id, payment_id, 0)


@pytest.mark.asyncio
async def test_enroll_duplicate_raises_conflict(
    enrollment_service: EnrollmentService,
    mock_repo: AsyncMock,
    student_id,
    course_id,
):
    mock_repo.create.side_effect = ConflictError("Already enrolled in this course")

    with pytest.raises(ConflictError, match="Already enrolled"):
        await enrollment_service.enroll(
            student_id=student_id,
            role="student",
            course_id=course_id,
            payment_id=None,
        )


@pytest.mark.asyncio
async def test_enroll_teacher_forbidden(
    enrollment_service: EnrollmentService,
):
    with pytest.raises(ForbiddenError, match="Only students"):
        await enrollment_service.enroll(
            student_id=uuid4(),
            role="teacher",
            course_id=uuid4(),
            payment_id=None,
        )


@pytest.mark.asyncio
async def test_list_my(
    enrollment_service: EnrollmentService,
    mock_repo: AsyncMock,
    sample_enrollment: Enrollment,
    student_id,
):
    mock_repo.list_by_student.return_value = ([sample_enrollment], 1)

    items, total = await enrollment_service.list_my(student_id, limit=20, offset=0)

    assert len(items) == 1
    assert total == 1
    mock_repo.list_by_student.assert_called_once_with(student_id, 20, 0)


@pytest.mark.asyncio
async def test_count_by_course(
    enrollment_service: EnrollmentService,
    mock_repo: AsyncMock,
    course_id,
):
    mock_repo.count_by_course.return_value = 42

    count = await enrollment_service.count_by_course(course_id)

    assert count == 42
    mock_repo.count_by_course.assert_called_once_with(course_id)
