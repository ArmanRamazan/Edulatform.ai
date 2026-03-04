import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ForbiddenError, NotFoundError
from common.security import create_access_token
from app.domain.bundle import BundleWithCourses, CourseBundle
from app.domain.course import Course, CourseLevel
from app.routes.bundles import router
from app.services.bundle_service import BundleService


@pytest.fixture
def mock_bundle_service():
    return AsyncMock(spec=BundleService)


@pytest.fixture
def test_app(mock_bundle_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._bundle_service = mock_bundle_service

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def teacher_id():
    return uuid4()


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


@pytest.fixture
def unverified_teacher_token():
    return create_access_token(
        str(uuid4()), "test-secret",
        extra_claims={"role": "teacher", "is_verified": False},
    )


def _make_course(teacher_id, course_id=None):
    return Course(
        id=course_id or uuid4(),
        teacher_id=teacher_id,
        title="Test Course",
        description="Desc",
        is_free=False,
        price=Decimal("29.99"),
        duration_minutes=60,
        level=CourseLevel.BEGINNER,
        created_at=datetime.now(timezone.utc),
    )


def _make_bundle_with_courses(teacher_id, bundle_id=None, num_courses=3):
    bundle = CourseBundle(
        id=bundle_id or uuid4(),
        teacher_id=teacher_id,
        title="Python Bundle",
        description="Learn Python",
        price=Decimal("49.99"),
        discount_percent=30,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    courses = [_make_course(teacher_id) for _ in range(num_courses)]
    return BundleWithCourses(bundle=bundle, courses=courses)


# --- POST /bundles ---


@pytest.mark.asyncio
async def test_create_bundle_success(client, mock_bundle_service, teacher_id, teacher_token):
    bwc = _make_bundle_with_courses(teacher_id)
    mock_bundle_service.create_bundle.return_value = bwc

    resp = await client.post("/bundles", json={
        "title": "Python Bundle",
        "description": "Learn Python",
        "price": "49.99",
        "discount_percent": 30,
        "course_ids": [str(uuid4()), str(uuid4()), str(uuid4())],
    }, headers={"Authorization": f"Bearer {teacher_token}"})

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Python Bundle"
    assert len(body["courses"]) == 3
    mock_bundle_service.create_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_create_bundle_not_verified(client, mock_bundle_service, unverified_teacher_token):
    mock_bundle_service.create_bundle.side_effect = ForbiddenError("Only verified teachers can create bundles")

    resp = await client.post("/bundles", json={
        "title": "Bundle",
        "price": "10.00",
        "discount_percent": 20,
        "course_ids": [str(uuid4()), str(uuid4())],
    }, headers={"Authorization": f"Bearer {unverified_teacher_token}"})

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_bundle_not_teacher(client, mock_bundle_service, student_token):
    mock_bundle_service.create_bundle.side_effect = ForbiddenError("Only teachers can create bundles")

    resp = await client.post("/bundles", json={
        "title": "Bundle",
        "price": "10.00",
        "discount_percent": 20,
        "course_ids": [str(uuid4()), str(uuid4())],
    }, headers={"Authorization": f"Bearer {student_token}"})

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_bundle_no_auth(client):
    resp = await client.post("/bundles", json={
        "title": "Bundle",
        "price": "10.00",
        "discount_percent": 20,
        "course_ids": [str(uuid4()), str(uuid4())],
    })

    assert resp.status_code == 422


# --- GET /bundles ---


@pytest.mark.asyncio
async def test_list_bundles(client, mock_bundle_service, teacher_id):
    bundle = CourseBundle(
        id=uuid4(),
        teacher_id=teacher_id,
        title="Python Bundle",
        description="Learn Python",
        price=Decimal("49.99"),
        discount_percent=30,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_bundle_service.list_bundles.return_value = ([bundle], 1)

    resp = await client.get("/bundles")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


# --- GET /bundles/{bundle_id} ---


@pytest.mark.asyncio
async def test_get_bundle_success(client, mock_bundle_service, teacher_id):
    bwc = _make_bundle_with_courses(teacher_id)
    mock_bundle_service.get_bundle.return_value = bwc

    resp = await client.get(f"/bundles/{bwc.bundle.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Python Bundle"
    assert len(body["courses"]) == 3


@pytest.mark.asyncio
async def test_get_bundle_not_found(client, mock_bundle_service):
    mock_bundle_service.get_bundle.side_effect = NotFoundError("Bundle not found")

    resp = await client.get(f"/bundles/{uuid4()}")

    assert resp.status_code == 404


# --- PUT /bundles/{bundle_id} ---


@pytest.mark.asyncio
async def test_update_bundle_owner(client, mock_bundle_service, teacher_id, teacher_token):
    bwc = _make_bundle_with_courses(teacher_id)
    mock_bundle_service.update_bundle.return_value = bwc

    resp = await client.put(f"/bundles/{bwc.bundle.id}", json={
        "title": "Updated Bundle",
    }, headers={"Authorization": f"Bearer {teacher_token}"})

    assert resp.status_code == 200
    mock_bundle_service.update_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_update_bundle_not_owner(client, mock_bundle_service, teacher_token):
    mock_bundle_service.update_bundle.side_effect = ForbiddenError("Only the bundle owner can update this bundle")

    resp = await client.put(f"/bundles/{uuid4()}", json={
        "title": "Updated",
    }, headers={"Authorization": f"Bearer {teacher_token}"})

    assert resp.status_code == 403


# --- DELETE /bundles/{bundle_id} ---


@pytest.mark.asyncio
async def test_delete_bundle_owner(client, mock_bundle_service, teacher_id, teacher_token):
    bundle_id = uuid4()
    mock_bundle_service.delete_bundle.return_value = None

    resp = await client.delete(
        f"/bundles/{bundle_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 204
    mock_bundle_service.delete_bundle.assert_called_once()


@pytest.mark.asyncio
async def test_delete_bundle_not_owner(client, mock_bundle_service, teacher_token):
    mock_bundle_service.delete_bundle.side_effect = ForbiddenError("Only the bundle owner can delete this bundle")

    resp = await client.delete(
        f"/bundles/{uuid4()}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 403
