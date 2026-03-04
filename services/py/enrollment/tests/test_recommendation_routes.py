import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.routes.recommendation_routes import router
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def mock_recommendation_service():
    return AsyncMock(spec=RecommendationService)


@pytest.fixture
def test_app(mock_recommendation_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._recommendation_service = mock_recommendation_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def student_id():
    return uuid4()


@pytest.fixture
def student_token(student_id):
    return create_access_token(
        str(student_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def course_id():
    return uuid4()


# --- GET /recommendations/courses/{course_id} (public) ---


@pytest.mark.asyncio
async def test_get_similar_courses_success(
    client, mock_recommendation_service, course_id
):
    cid1, cid2 = uuid4(), uuid4()
    mock_recommendation_service.get_similar_courses.return_value = [
        {"course_id": cid1, "co_enrollment_count": 10},
        {"course_id": cid2, "co_enrollment_count": 5},
    ]

    resp = await client.get(f"/recommendations/courses/{course_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["course_id"] == str(cid1)
    assert body["items"][0]["co_enrollment_count"] == 10


@pytest.mark.asyncio
async def test_get_similar_courses_empty(
    client, mock_recommendation_service, course_id
):
    mock_recommendation_service.get_similar_courses.return_value = []

    resp = await client.get(f"/recommendations/courses/{course_id}")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_similar_courses_custom_limit(
    client, mock_recommendation_service, course_id
):
    mock_recommendation_service.get_similar_courses.return_value = []

    resp = await client.get(f"/recommendations/courses/{course_id}?limit=3")

    assert resp.status_code == 200
    mock_recommendation_service.get_similar_courses.assert_called_once_with(
        course_id, limit=3
    )


@pytest.mark.asyncio
async def test_get_similar_courses_no_auth_required(
    client, mock_recommendation_service, course_id
):
    """This endpoint is public, no auth header needed."""
    mock_recommendation_service.get_similar_courses.return_value = []

    resp = await client.get(f"/recommendations/courses/{course_id}")

    assert resp.status_code == 200


# --- GET /recommendations/me (auth required) ---


@pytest.mark.asyncio
async def test_get_personalized_recommendations_success(
    client, mock_recommendation_service, student_token, student_id
):
    cid1, cid2 = uuid4(), uuid4()
    mock_recommendation_service.get_personalized_recommendations.return_value = [
        {"course_id": cid1, "co_enrollment_count": 20},
        {"course_id": cid2, "co_enrollment_count": 15},
    ]

    resp = await client.get(
        "/recommendations/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["course_id"] == str(cid1)


@pytest.mark.asyncio
async def test_get_personalized_recommendations_empty(
    client, mock_recommendation_service, student_token, student_id
):
    mock_recommendation_service.get_personalized_recommendations.return_value = []

    resp = await client.get(
        "/recommendations/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_get_personalized_recommendations_custom_limit(
    client, mock_recommendation_service, student_token, student_id
):
    mock_recommendation_service.get_personalized_recommendations.return_value = []

    resp = await client.get(
        "/recommendations/me?limit=3",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    mock_recommendation_service.get_personalized_recommendations.assert_called_once_with(
        student_id, limit=3
    )


@pytest.mark.asyncio
async def test_get_personalized_recommendations_no_auth(client):
    """Auth is required for /me endpoint."""
    resp = await client.get("/recommendations/me")

    assert resp.status_code == 422
