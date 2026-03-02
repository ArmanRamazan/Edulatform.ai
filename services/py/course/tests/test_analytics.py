import pytest
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError
from common.security import create_access_token
from app.domain.course import CourseAnalytics, TeacherAnalyticsSummary
from app.repositories.course_repo import CourseRepository
from app.services.course_service import CourseService


# --- Unit tests for CourseService.get_teacher_analytics ---


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=CourseRepository)


@pytest.fixture
def course_service(mock_repo):
    return CourseService(repo=mock_repo, cache=None)


@pytest.fixture
def teacher_id():
    return uuid4()


@pytest.mark.asyncio
async def test_get_teacher_analytics_success(course_service, mock_repo, teacher_id):
    course1_id = uuid4()
    course2_id = uuid4()
    mock_repo.get_analytics_by_teacher.return_value = [
        {
            "course_id": course1_id,
            "title": "Course A",
            "avg_rating": Decimal("4.50"),
            "review_count": 10,
            "module_count": 3,
            "lesson_count": 12,
        },
        {
            "course_id": course2_id,
            "title": "Course B",
            "avg_rating": Decimal("3.50"),
            "review_count": 5,
            "module_count": 2,
            "lesson_count": 8,
        },
    ]

    result = await course_service.get_teacher_analytics(teacher_id, "teacher")

    assert result.total_courses == 2
    assert result.total_lessons == 20
    assert result.total_reviews == 15
    assert result.avg_rating == Decimal("4.00")
    assert len(result.courses) == 2
    mock_repo.get_analytics_by_teacher.assert_awaited_once_with(teacher_id)


@pytest.mark.asyncio
async def test_get_teacher_analytics_student_forbidden(course_service, teacher_id):
    with pytest.raises(ForbiddenError):
        await course_service.get_teacher_analytics(teacher_id, "student")


@pytest.mark.asyncio
async def test_get_teacher_analytics_empty(course_service, mock_repo, teacher_id):
    mock_repo.get_analytics_by_teacher.return_value = []

    result = await course_service.get_teacher_analytics(teacher_id, "teacher")

    assert result.total_courses == 0
    assert result.total_lessons == 0
    assert result.avg_rating is None
    assert result.total_reviews == 0
    assert result.courses == []


# --- Route tests for GET /analytics/teacher ---


@pytest.fixture
def mock_service():
    return AsyncMock(spec=CourseService)


@pytest.fixture
def test_app(mock_service):
    from app.routes.analytics import router

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._course_service = mock_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def teacher_token(teacher_id):
    return create_access_token(
        str(teacher_id), "test-secret",
        extra_claims={"role": "teacher", "is_verified": True},
    )


@pytest.fixture
def student_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.mark.asyncio
async def test_analytics_teacher_success(client, mock_service, teacher_token):
    mock_service.get_teacher_analytics.return_value = TeacherAnalyticsSummary(
        total_courses=2,
        total_lessons=20,
        avg_rating=Decimal("4.00"),
        total_reviews=15,
        courses=[
            CourseAnalytics(
                course_id=uuid4(),
                title="Course A",
                avg_rating=Decimal("4.50"),
                review_count=10,
                module_count=3,
                lesson_count=12,
            ),
            CourseAnalytics(
                course_id=uuid4(),
                title="Course B",
                avg_rating=Decimal("3.50"),
                review_count=5,
                module_count=2,
                lesson_count=8,
            ),
        ],
    )

    resp = await client.get(
        "/analytics/teacher",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_courses"] == 2
    assert body["total_lessons"] == 20


@pytest.mark.asyncio
async def test_analytics_no_auth(client):
    resp = await client.get("/analytics/teacher")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analytics_student_forbidden(client, mock_service, student_token):
    mock_service.get_teacher_analytics.side_effect = ForbiddenError(
        "Only teachers can view analytics"
    )

    resp = await client.get(
        "/analytics/teacher",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403
