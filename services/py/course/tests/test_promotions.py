import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    register_error_handlers,
)
from common.security import create_access_token
from app.domain.course import Course, CourseLevel
from app.domain.promotion import ActivePromotion, CoursePromotion
from app.repositories.course_repo import CourseRepository
from app.repositories.promotion_repo import PromotionRepository
from app.services.promotion_service import PromotionService
from app.routes.promotions import router as promotions_router


# ─── helpers ───


def _make_course(teacher_id, course_id=None, price=Decimal("49.99"), is_free=False):
    return Course(
        id=course_id or uuid4(),
        teacher_id=teacher_id,
        title="Test Course",
        description="Desc",
        is_free=is_free,
        price=price,
        duration_minutes=60,
        level=CourseLevel.BEGINNER,
        created_at=datetime.now(timezone.utc),
    )


def _make_promotion(
    course_id,
    created_by,
    promotion_id=None,
    original_price=Decimal("49.99"),
    promo_price=Decimal("29.99"),
    starts_at=None,
    ends_at=None,
    is_active=True,
):
    now = datetime.now(timezone.utc)
    return CoursePromotion(
        id=promotion_id or uuid4(),
        course_id=course_id,
        original_price=original_price,
        promo_price=promo_price,
        starts_at=starts_at or now - timedelta(hours=1),
        ends_at=ends_at or now + timedelta(days=7),
        is_active=is_active,
        created_by=created_by,
        created_at=now,
    )


# ─── service fixtures ───


@pytest.fixture
def teacher_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def promotion_id():
    return uuid4()


@pytest.fixture
def mock_promo_repo():
    return AsyncMock(spec=PromotionRepository)


@pytest.fixture
def mock_course_repo():
    return AsyncMock(spec=CourseRepository)


@pytest.fixture
def promo_service(mock_promo_repo, mock_course_repo):
    return PromotionService(repo=mock_promo_repo, course_repo=mock_course_repo)


# ─── service: create_promotion ───


@pytest.mark.asyncio
async def test_create_promotion_success(
    promo_service, mock_promo_repo, mock_course_repo, teacher_id, course_id, promotion_id,
):
    course = _make_course(teacher_id, course_id)
    mock_course_repo.get_by_id.return_value = course
    mock_promo_repo.get_active_promotion.return_value = None

    now = datetime.now(timezone.utc)
    starts_at = now + timedelta(hours=1)
    ends_at = now + timedelta(days=7)
    promo = _make_promotion(course_id, teacher_id, promotion_id, starts_at=starts_at, ends_at=ends_at)
    mock_promo_repo.create_promotion.return_value = promo

    result = await promo_service.create_promotion(
        teacher_id=teacher_id,
        course_id=course_id,
        promo_price=Decimal("29.99"),
        starts_at=starts_at,
        ends_at=ends_at,
    )

    assert result.id == promotion_id
    assert result.original_price == Decimal("49.99")
    mock_promo_repo.create_promotion.assert_called_once()


@pytest.mark.asyncio
async def test_create_promotion_not_owner(
    promo_service, mock_course_repo, teacher_id, course_id,
):
    other_teacher = uuid4()
    course = _make_course(other_teacher, course_id)
    mock_course_repo.get_by_id.return_value = course

    with pytest.raises(ForbiddenError, match="Only the course owner"):
        await promo_service.create_promotion(
            teacher_id=teacher_id,
            course_id=course_id,
            promo_price=Decimal("29.99"),
            starts_at=datetime.now(timezone.utc),
            ends_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


@pytest.mark.asyncio
async def test_create_promotion_free_course(
    promo_service, mock_course_repo, teacher_id, course_id,
):
    course = _make_course(teacher_id, course_id, is_free=True, price=None)
    mock_course_repo.get_by_id.return_value = course

    with pytest.raises(AppError, match="Cannot create promotion for a free course"):
        await promo_service.create_promotion(
            teacher_id=teacher_id,
            course_id=course_id,
            promo_price=Decimal("0"),
            starts_at=datetime.now(timezone.utc),
            ends_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


@pytest.mark.asyncio
async def test_create_promotion_price_too_high(
    promo_service, mock_course_repo, teacher_id, course_id,
):
    course = _make_course(teacher_id, course_id, price=Decimal("49.99"))
    mock_course_repo.get_by_id.return_value = course

    with pytest.raises(AppError, match="Promo price must be less than"):
        await promo_service.create_promotion(
            teacher_id=teacher_id,
            course_id=course_id,
            promo_price=Decimal("49.99"),
            starts_at=datetime.now(timezone.utc),
            ends_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


@pytest.mark.asyncio
async def test_create_promotion_overlapping(
    promo_service, mock_promo_repo, mock_course_repo, teacher_id, course_id,
):
    course = _make_course(teacher_id, course_id)
    mock_course_repo.get_by_id.return_value = course

    existing = _make_promotion(course_id, teacher_id)
    mock_promo_repo.get_active_promotion.return_value = existing

    with pytest.raises(ConflictError, match="already has an active promotion"):
        await promo_service.create_promotion(
            teacher_id=teacher_id,
            course_id=course_id,
            promo_price=Decimal("29.99"),
            starts_at=datetime.now(timezone.utc),
            ends_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


@pytest.mark.asyncio
async def test_create_promotion_invalid_dates(
    promo_service, mock_course_repo, teacher_id, course_id,
):
    course = _make_course(teacher_id, course_id)
    mock_course_repo.get_by_id.return_value = course

    now = datetime.now(timezone.utc)
    with pytest.raises(AppError, match="ends_at must be after starts_at"):
        await promo_service.create_promotion(
            teacher_id=teacher_id,
            course_id=course_id,
            promo_price=Decimal("29.99"),
            starts_at=now + timedelta(days=7),
            ends_at=now,
        )


# ─── service: get_active_promotion ───


@pytest.mark.asyncio
async def test_get_active_promotion(promo_service, mock_promo_repo, course_id, teacher_id):
    promo = _make_promotion(course_id, teacher_id)
    mock_promo_repo.get_active_promotion.return_value = promo

    result = await promo_service.get_active_promotion(course_id)

    assert result is not None
    assert result.promo_price == Decimal("29.99")
    assert result.ends_at == promo.ends_at


@pytest.mark.asyncio
async def test_get_active_promotion_expired(promo_service, mock_promo_repo, course_id):
    mock_promo_repo.get_active_promotion.return_value = None

    result = await promo_service.get_active_promotion(course_id)

    assert result is None


# ─── service: get_course_promotions ───


@pytest.mark.asyncio
async def test_get_course_promotions_owner(
    promo_service, mock_promo_repo, mock_course_repo, teacher_id, course_id,
):
    course = _make_course(teacher_id, course_id)
    mock_course_repo.get_by_id.return_value = course
    promos = [_make_promotion(course_id, teacher_id) for _ in range(3)]
    mock_promo_repo.get_course_promotions.return_value = promos

    result = await promo_service.get_course_promotions(teacher_id, course_id)

    assert len(result) == 3


# ─── service: delete_promotion ───


@pytest.mark.asyncio
async def test_delete_promotion_owner(
    promo_service, mock_promo_repo, mock_course_repo, teacher_id, course_id, promotion_id,
):
    promo = _make_promotion(course_id, teacher_id, promotion_id)
    mock_promo_repo.get_promotion.return_value = promo
    course = _make_course(teacher_id, course_id)
    mock_course_repo.get_by_id.return_value = course
    mock_promo_repo.delete_promotion.return_value = True

    await promo_service.delete_promotion(teacher_id, promotion_id)

    mock_promo_repo.delete_promotion.assert_called_once_with(promotion_id)


@pytest.mark.asyncio
async def test_delete_promotion_not_owner(
    promo_service, mock_promo_repo, mock_course_repo, teacher_id, course_id, promotion_id,
):
    other_teacher = uuid4()
    promo = _make_promotion(course_id, other_teacher, promotion_id)
    mock_promo_repo.get_promotion.return_value = promo
    course = _make_course(other_teacher, course_id)
    mock_course_repo.get_by_id.return_value = course

    with pytest.raises(ForbiddenError, match="Only the course owner"):
        await promo_service.delete_promotion(teacher_id, promotion_id)


# ─── route fixtures ───


@pytest.fixture
def mock_promo_service():
    return AsyncMock(spec=PromotionService)


@pytest.fixture
def route_app(mock_promo_service):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(promotions_router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._promotion_service = mock_promo_service
    return app


@pytest.fixture
async def client(route_app):
    transport = ASGITransport(app=route_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def teacher_token(teacher_id):
    return create_access_token(
        str(teacher_id), "test-secret",
        extra_claims={"role": "teacher", "is_verified": True},
    )


# ─── route: POST /courses/{course_id}/promotions ───


@pytest.mark.asyncio
async def test_route_create_promotion_success(client, mock_promo_service, teacher_id, course_id, teacher_token):
    now = datetime.now(timezone.utc)
    promo = _make_promotion(course_id, teacher_id, starts_at=now, ends_at=now + timedelta(days=7))
    mock_promo_service.create_promotion.return_value = promo

    resp = await client.post(
        f"/courses/{course_id}/promotions",
        json={
            "promo_price": "29.99",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["promo_price"] == "29.99"
    assert body["course_id"] == str(course_id)


@pytest.mark.asyncio
async def test_route_create_promotion_forbidden(client, mock_promo_service, course_id, teacher_token):
    mock_promo_service.create_promotion.side_effect = ForbiddenError("Only the course owner")

    now = datetime.now(timezone.utc)
    resp = await client.post(
        f"/courses/{course_id}/promotions",
        json={
            "promo_price": "29.99",
            "starts_at": now.isoformat(),
            "ends_at": (now + timedelta(days=7)).isoformat(),
        },
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 403


# ─── route: GET /courses/{course_id}/promotions ───


@pytest.mark.asyncio
async def test_route_get_promotions_public(client, mock_promo_service, course_id):
    now = datetime.now(timezone.utc)
    active = _make_promotion(course_id, uuid4(), starts_at=now - timedelta(hours=1), ends_at=now + timedelta(days=7))
    mock_promo_service.get_active_promotion.return_value = ActivePromotion(
        promo_price=active.promo_price, ends_at=active.ends_at,
    )

    resp = await client.get(f"/courses/{course_id}/promotions")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1


# ─── route: DELETE /promotions/{promotion_id} ───


@pytest.mark.asyncio
async def test_route_delete_promotion_owner(client, mock_promo_service, promotion_id, teacher_token):
    mock_promo_service.delete_promotion.return_value = None

    resp = await client.delete(
        f"/promotions/{promotion_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 204
    mock_promo_service.delete_promotion.assert_called_once()


@pytest.mark.asyncio
async def test_route_delete_promotion_not_owner(client, mock_promo_service, promotion_id, teacher_token):
    mock_promo_service.delete_promotion.side_effect = ForbiddenError("Only the course owner")

    resp = await client.delete(
        f"/promotions/{promotion_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )

    assert resp.status_code == 403


# ─── course response with active_promotion ───


@pytest.mark.asyncio
async def test_course_response_includes_promotion():
    """CourseResponse with active_promotion field serializes correctly."""
    from app.domain.course import CourseResponse
    from app.domain.promotion import ActivePromotionResponse

    now = datetime.now(timezone.utc)
    resp = CourseResponse(
        id=uuid4(),
        teacher_id=uuid4(),
        title="Test",
        description="Desc",
        is_free=False,
        price=Decimal("49.99"),
        duration_minutes=60,
        level=CourseLevel.BEGINNER,
        created_at=now,
        active_promotion=ActivePromotionResponse(
            promo_price=Decimal("29.99"),
            ends_at=now + timedelta(days=7),
        ),
    )
    data = resp.model_dump(mode="json")
    assert data["active_promotion"]["promo_price"] == "29.99"
    assert data["active_promotion"]["ends_at"] is not None


@pytest.mark.asyncio
async def test_course_response_no_promotion():
    """CourseResponse without promotion has active_promotion=None."""
    from app.domain.course import CourseResponse

    resp = CourseResponse(
        id=uuid4(),
        teacher_id=uuid4(),
        title="Test",
        description="Desc",
        is_free=False,
        price=Decimal("49.99"),
        duration_minutes=60,
        level=CourseLevel.BEGINNER,
        created_at=datetime.now(timezone.utc),
    )
    assert resp.active_promotion is None
