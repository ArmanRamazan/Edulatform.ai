import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import AppError, ForbiddenError, NotFoundError
from app.domain.bundle import BundleWithCourses, CourseBundle
from app.domain.course import Course, CourseLevel
from app.repositories.bundle_repo import BundleRepository
from app.repositories.course_repo import CourseRepository
from app.services.bundle_service import BundleService


@pytest.fixture
def teacher_id():
    return uuid4()


@pytest.fixture
def bundle_id():
    return uuid4()


@pytest.fixture
def mock_bundle_repo():
    return AsyncMock(spec=BundleRepository)


@pytest.fixture
def mock_course_repo():
    return AsyncMock(spec=CourseRepository)


@pytest.fixture
def bundle_service(mock_bundle_repo, mock_course_repo):
    return BundleService(repo=mock_bundle_repo, course_repo=mock_course_repo)


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


def _make_bundle(teacher_id, bundle_id=None):
    return CourseBundle(
        id=bundle_id or uuid4(),
        teacher_id=teacher_id,
        title="Python Bundle",
        description="Learn Python",
        price=Decimal("49.99"),
        discount_percent=30,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


# --- create_bundle ---


@pytest.mark.asyncio
async def test_create_bundle_success(bundle_service, mock_bundle_repo, mock_course_repo, teacher_id, bundle_id):
    course_ids = [uuid4(), uuid4(), uuid4()]
    courses = [_make_course(teacher_id, cid) for cid in course_ids]
    bundle = _make_bundle(teacher_id, bundle_id)
    bundle_with_courses = BundleWithCourses(bundle=bundle, courses=courses)

    mock_course_repo.get_by_id.side_effect = lambda cid: next(
        (c for c in courses if c.id == cid), None
    )
    mock_bundle_repo.create_bundle_with_courses.return_value = bundle_with_courses

    result = await bundle_service.create_bundle(
        teacher_id=teacher_id,
        role="teacher",
        is_verified=True,
        title="Python Bundle",
        description="Learn Python",
        price=Decimal("49.99"),
        discount_percent=30,
        course_ids=course_ids,
    )

    assert result.bundle.id == bundle_id
    assert len(result.courses) == 3
    mock_bundle_repo.create_bundle_with_courses.assert_called_once()


@pytest.mark.asyncio
async def test_create_bundle_not_verified(bundle_service, teacher_id):
    with pytest.raises(ForbiddenError, match="Only verified teachers can create bundles"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=False,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[uuid4(), uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_not_teacher(bundle_service, teacher_id):
    with pytest.raises(ForbiddenError, match="Only teachers can create bundles"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="student",
            is_verified=False,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[uuid4(), uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_too_few_courses(bundle_service, teacher_id):
    with pytest.raises(AppError, match="Bundle must contain between 2 and 10 courses"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_too_many_courses(bundle_service, teacher_id):
    with pytest.raises(AppError, match="Bundle must contain between 2 and 10 courses"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[uuid4() for _ in range(11)],
        )


@pytest.mark.asyncio
async def test_create_bundle_course_not_found(bundle_service, mock_course_repo, teacher_id):
    mock_course_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Course .* not found"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[uuid4(), uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_course_not_owned(bundle_service, mock_course_repo, teacher_id):
    other_teacher = uuid4()
    course = _make_course(other_teacher)
    mock_course_repo.get_by_id.return_value = course

    with pytest.raises(ForbiddenError, match="All courses in a bundle must belong to you"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=20,
            course_ids=[course.id, uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_invalid_price(bundle_service, teacher_id):
    with pytest.raises(AppError, match="Price must be greater than 0"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("0"),
            discount_percent=20,
            course_ids=[uuid4(), uuid4()],
        )


@pytest.mark.asyncio
async def test_create_bundle_invalid_discount(bundle_service, teacher_id):
    with pytest.raises(AppError, match="Discount must be between 1 and 99"):
        await bundle_service.create_bundle(
            teacher_id=teacher_id,
            role="teacher",
            is_verified=True,
            title="Bundle",
            description="",
            price=Decimal("10.00"),
            discount_percent=100,
            course_ids=[uuid4(), uuid4()],
        )


# --- get_bundle ---


@pytest.mark.asyncio
async def test_get_bundle_success(bundle_service, mock_bundle_repo, teacher_id, bundle_id):
    courses = [_make_course(teacher_id) for _ in range(2)]
    bundle = _make_bundle(teacher_id, bundle_id)
    bwc = BundleWithCourses(bundle=bundle, courses=courses)
    mock_bundle_repo.get_bundle_with_courses.return_value = bwc

    result = await bundle_service.get_bundle(bundle_id)

    assert result.bundle.id == bundle_id
    assert len(result.courses) == 2
    mock_bundle_repo.get_bundle_with_courses.assert_called_once_with(bundle_id)


@pytest.mark.asyncio
async def test_get_bundle_not_found(bundle_service, mock_bundle_repo):
    mock_bundle_repo.get_bundle_with_courses.return_value = None

    with pytest.raises(NotFoundError, match="Bundle not found"):
        await bundle_service.get_bundle(uuid4())


# --- list_bundles ---


@pytest.mark.asyncio
async def test_list_bundles(bundle_service, mock_bundle_repo, teacher_id):
    bundle = _make_bundle(teacher_id)
    mock_bundle_repo.list_bundles.return_value = ([bundle], 1)

    items, total = await bundle_service.list_bundles(limit=20, offset=0)

    assert len(items) == 1
    assert total == 1


# --- update_bundle ---


@pytest.mark.asyncio
async def test_update_bundle_owner(bundle_service, mock_bundle_repo, teacher_id, bundle_id):
    bundle = _make_bundle(teacher_id, bundle_id)
    mock_bundle_repo.get_bundle.return_value = bundle
    courses = [_make_course(teacher_id) for _ in range(2)]
    updated_bwc = BundleWithCourses(bundle=bundle, courses=courses)
    mock_bundle_repo.update_bundle.return_value = bundle
    mock_bundle_repo.get_bundle_with_courses.return_value = updated_bwc

    result = await bundle_service.update_bundle(
        teacher_id=teacher_id,
        bundle_id=bundle_id,
        title="Updated Bundle",
    )

    assert result.bundle.id == bundle_id


@pytest.mark.asyncio
async def test_update_bundle_not_owner(bundle_service, mock_bundle_repo, teacher_id, bundle_id):
    other_teacher = uuid4()
    bundle = _make_bundle(other_teacher, bundle_id)
    mock_bundle_repo.get_bundle.return_value = bundle

    with pytest.raises(ForbiddenError, match="Only the bundle owner can update this bundle"):
        await bundle_service.update_bundle(
            teacher_id=teacher_id,
            bundle_id=bundle_id,
            title="Updated",
        )


@pytest.mark.asyncio
async def test_update_bundle_not_found(bundle_service, mock_bundle_repo, teacher_id):
    mock_bundle_repo.get_bundle.return_value = None

    with pytest.raises(NotFoundError, match="Bundle not found"):
        await bundle_service.update_bundle(
            teacher_id=teacher_id,
            bundle_id=uuid4(),
            title="Updated",
        )


# --- delete_bundle ---


@pytest.mark.asyncio
async def test_delete_bundle_owner(bundle_service, mock_bundle_repo, teacher_id, bundle_id):
    bundle = _make_bundle(teacher_id, bundle_id)
    mock_bundle_repo.get_bundle.return_value = bundle
    mock_bundle_repo.delete_bundle.return_value = True

    await bundle_service.delete_bundle(teacher_id=teacher_id, bundle_id=bundle_id)

    mock_bundle_repo.delete_bundle.assert_called_once_with(bundle_id)


@pytest.mark.asyncio
async def test_delete_bundle_not_owner(bundle_service, mock_bundle_repo, teacher_id, bundle_id):
    other_teacher = uuid4()
    bundle = _make_bundle(other_teacher, bundle_id)
    mock_bundle_repo.get_bundle.return_value = bundle

    with pytest.raises(ForbiddenError, match="Only the bundle owner can delete this bundle"):
        await bundle_service.delete_bundle(teacher_id=teacher_id, bundle_id=bundle_id)
