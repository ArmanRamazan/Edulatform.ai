import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers, ConflictError, NotFoundError
from common.security import create_access_token
from app.domain.wishlist import WishlistItem
from app.routes.wishlist_routes import router
from app.services.wishlist_service import WishlistService


@pytest.fixture
def mock_wishlist_svc():
    return AsyncMock(spec=WishlistService)


@pytest.fixture
def test_app(mock_wishlist_svc):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._wishlist_service = mock_wishlist_svc

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def student_token(user_id):
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def sample_wishlist_item(user_id, course_id):
    return WishlistItem(
        id=uuid4(),
        user_id=user_id,
        course_id=course_id,
        course_title="Python Basics",
        course_description="Learn Python",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_add_to_wishlist(client, mock_wishlist_svc, sample_wishlist_item, student_token, course_id):
    mock_wishlist_svc.add_to_wishlist.return_value = sample_wishlist_item

    resp = await client.post(
        "/wishlist",
        json={"course_id": str(course_id)},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["course_id"] == str(course_id)
    assert body["course_title"] == "Python Basics"


@pytest.mark.asyncio
async def test_add_to_wishlist_duplicate(client, mock_wishlist_svc, student_token, course_id):
    mock_wishlist_svc.add_to_wishlist.side_effect = ConflictError("Course already in wishlist")

    resp = await client.post(
        "/wishlist",
        json={"course_id": str(course_id)},
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_to_wishlist_no_auth(client, course_id):
    resp = await client.post("/wishlist", json={"course_id": str(course_id)})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_remove_from_wishlist(client, mock_wishlist_svc, student_token, course_id):
    mock_wishlist_svc.remove_from_wishlist.return_value = None

    resp = await client.delete(
        f"/wishlist/{course_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_from_wishlist_not_found(client, mock_wishlist_svc, student_token, course_id):
    mock_wishlist_svc.remove_from_wishlist.side_effect = NotFoundError("Course not in wishlist")

    resp = await client.delete(
        f"/wishlist/{course_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_my_wishlist(client, mock_wishlist_svc, sample_wishlist_item, student_token):
    mock_wishlist_svc.get_my_wishlist.return_value = ([sample_wishlist_item], 1)

    resp = await client.get(
        "/wishlist/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["course_title"] == "Python Basics"


@pytest.mark.asyncio
async def test_get_my_wishlist_empty(client, mock_wishlist_svc, student_token):
    mock_wishlist_svc.get_my_wishlist.return_value = ([], 0)

    resp = await client.get(
        "/wishlist/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_check_in_wishlist_true(client, mock_wishlist_svc, student_token, course_id):
    mock_wishlist_svc.is_in_wishlist.return_value = True

    resp = await client.get(
        f"/wishlist/check/{course_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["in_wishlist"] is True


@pytest.mark.asyncio
async def test_check_in_wishlist_false(client, mock_wishlist_svc, student_token, course_id):
    mock_wishlist_svc.is_in_wishlist.return_value = False

    resp = await client.get(
        f"/wishlist/check/{course_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["in_wishlist"] is False
