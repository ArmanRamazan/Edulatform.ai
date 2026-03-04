import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.repositories.recommendation_repo import RecommendationRepository
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def mock_recommendation_repo():
    return AsyncMock(spec=RecommendationRepository)


@pytest.fixture
def recommendation_service(mock_recommendation_repo):
    return RecommendationService(repo=mock_recommendation_repo)


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def student_id():
    return uuid4()


@pytest.mark.asyncio
async def test_get_similar_courses(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    course_id,
):
    expected = [
        {"course_id": uuid4(), "co_enrollment_count": 10},
        {"course_id": uuid4(), "co_enrollment_count": 5},
    ]
    mock_recommendation_repo.get_similar_courses.return_value = expected

    result = await recommendation_service.get_similar_courses(course_id, limit=5)

    assert result == expected
    mock_recommendation_repo.get_similar_courses.assert_called_once_with(course_id, 5)


@pytest.mark.asyncio
async def test_get_similar_courses_empty(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    course_id,
):
    mock_recommendation_repo.get_similar_courses.return_value = []

    result = await recommendation_service.get_similar_courses(course_id, limit=5)

    assert result == []


@pytest.mark.asyncio
async def test_get_similar_courses_custom_limit(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    course_id,
):
    mock_recommendation_repo.get_similar_courses.return_value = []

    await recommendation_service.get_similar_courses(course_id, limit=3)

    mock_recommendation_repo.get_similar_courses.assert_called_once_with(course_id, 3)


@pytest.mark.asyncio
async def test_get_personalized_recommendations(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    student_id,
):
    expected = [
        {"course_id": uuid4(), "co_enrollment_count": 20},
        {"course_id": uuid4(), "co_enrollment_count": 15},
        {"course_id": uuid4(), "co_enrollment_count": 8},
    ]
    mock_recommendation_repo.get_personalized_recommendations.return_value = expected

    result = await recommendation_service.get_personalized_recommendations(
        student_id, limit=10
    )

    assert result == expected
    mock_recommendation_repo.get_personalized_recommendations.assert_called_once_with(
        student_id, 10
    )


@pytest.mark.asyncio
async def test_get_personalized_recommendations_empty(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    student_id,
):
    mock_recommendation_repo.get_personalized_recommendations.return_value = []

    result = await recommendation_service.get_personalized_recommendations(
        student_id, limit=10
    )

    assert result == []


@pytest.mark.asyncio
async def test_get_personalized_recommendations_custom_limit(
    recommendation_service: RecommendationService,
    mock_recommendation_repo: AsyncMock,
    student_id,
):
    mock_recommendation_repo.get_personalized_recommendations.return_value = []

    await recommendation_service.get_personalized_recommendations(student_id, limit=3)

    mock_recommendation_repo.get_personalized_recommendations.assert_called_once_with(
        student_id, 3
    )
