import pytest
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import ConflictError, ForbiddenError
from app.domain.course import Course
from app.domain.review import Review
from app.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_create_review(review_service: ReviewService, mock_review_repo: AsyncMock, mock_repo: AsyncMock, sample_course: Course, sample_review: Review, student_id, course_id):
    mock_repo.get_by_id.return_value = sample_course
    mock_review_repo.create.return_value = sample_review
    mock_review_repo.get_avg.return_value = (Decimal("5.00"), 1)

    result = await review_service.create(
        student_id=student_id, role="student",
        course_id=course_id, rating=5, comment="Отличный курс!",
    )

    assert result.rating == 5
    mock_repo.update_rating.assert_called_once()


@pytest.mark.asyncio
async def test_create_review_duplicate(review_service: ReviewService, mock_review_repo: AsyncMock, mock_repo: AsyncMock, sample_course: Course, student_id, course_id):
    mock_repo.get_by_id.return_value = sample_course
    mock_review_repo.create.side_effect = ConflictError("You already reviewed this course")

    with pytest.raises(ConflictError, match="already reviewed"):
        await review_service.create(
            student_id=student_id, role="student",
            course_id=course_id, rating=4, comment="",
        )


@pytest.mark.asyncio
async def test_list_reviews(review_service: ReviewService, mock_review_repo: AsyncMock, sample_review: Review, course_id):
    mock_review_repo.list_by_course.return_value = ([sample_review], 1)

    items, total = await review_service.list_by_course(course_id)

    assert len(items) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_create_review_teacher_forbidden(review_service: ReviewService):
    with pytest.raises(ForbiddenError, match="Only students"):
        await review_service.create(
            student_id=uuid4(), role="teacher",
            course_id=uuid4(), rating=5, comment="",
        )
