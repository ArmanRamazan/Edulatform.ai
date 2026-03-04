import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import ConflictError, NotFoundError
from app.domain.course import Course, CourseLevel
from app.domain.wishlist import WishlistItem
from app.repositories.wishlist_repo import WishlistRepository
from app.repositories.course_repo import CourseRepository
from app.services.wishlist_service import WishlistService


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_wishlist_repo():
    return AsyncMock(spec=WishlistRepository)


@pytest.fixture
def mock_course_repo():
    return AsyncMock(spec=CourseRepository)


@pytest.fixture
def wishlist_service(mock_wishlist_repo, mock_course_repo):
    return WishlistService(repo=mock_wishlist_repo, course_repo=mock_course_repo)


@pytest.fixture
def sample_course(course_id):
    return Course(
        id=course_id,
        teacher_id=uuid4(),
        title="Python Basics",
        description="Learn Python",
        is_free=True,
        price=None,
        duration_minutes=120,
        level=CourseLevel.BEGINNER,
        created_at=datetime.now(timezone.utc),
    )


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
async def test_add_to_wishlist(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    mock_course_repo: AsyncMock,
    sample_course: Course,
    sample_wishlist_item: WishlistItem,
    user_id,
    course_id,
):
    mock_course_repo.get_by_id.return_value = sample_course
    mock_wishlist_repo.add.return_value = sample_wishlist_item

    result = await wishlist_service.add_to_wishlist(user_id=user_id, course_id=course_id)

    assert result.course_id == course_id
    assert result.user_id == user_id
    mock_course_repo.get_by_id.assert_called_once_with(course_id)
    mock_wishlist_repo.add.assert_called_once_with(user_id, course_id)


@pytest.mark.asyncio
async def test_add_to_wishlist_course_not_found(
    wishlist_service: WishlistService,
    mock_course_repo: AsyncMock,
    user_id,
):
    mock_course_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Course not found"):
        await wishlist_service.add_to_wishlist(user_id=user_id, course_id=uuid4())


@pytest.mark.asyncio
async def test_add_to_wishlist_duplicate(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    mock_course_repo: AsyncMock,
    sample_course: Course,
    user_id,
    course_id,
):
    mock_course_repo.get_by_id.return_value = sample_course
    mock_wishlist_repo.add.side_effect = ConflictError("Course already in wishlist")

    with pytest.raises(ConflictError, match="already in wishlist"):
        await wishlist_service.add_to_wishlist(user_id=user_id, course_id=course_id)


@pytest.mark.asyncio
async def test_remove_from_wishlist(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    user_id,
    course_id,
):
    mock_wishlist_repo.remove.return_value = True

    await wishlist_service.remove_from_wishlist(user_id=user_id, course_id=course_id)

    mock_wishlist_repo.remove.assert_called_once_with(user_id, course_id)


@pytest.mark.asyncio
async def test_remove_from_wishlist_not_found(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    user_id,
    course_id,
):
    mock_wishlist_repo.remove.return_value = False

    with pytest.raises(NotFoundError, match="not in wishlist"):
        await wishlist_service.remove_from_wishlist(user_id=user_id, course_id=course_id)


@pytest.mark.asyncio
async def test_get_my_wishlist(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    sample_wishlist_item: WishlistItem,
    user_id,
):
    mock_wishlist_repo.get_by_user.return_value = ([sample_wishlist_item], 1)

    items, total = await wishlist_service.get_my_wishlist(user_id=user_id)

    assert len(items) == 1
    assert total == 1
    assert items[0].course_id == sample_wishlist_item.course_id
    mock_wishlist_repo.get_by_user.assert_called_once_with(user_id, 20, 0)


@pytest.mark.asyncio
async def test_get_my_wishlist_with_pagination(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    user_id,
):
    mock_wishlist_repo.get_by_user.return_value = ([], 0)

    items, total = await wishlist_service.get_my_wishlist(user_id=user_id, limit=10, offset=5)

    assert len(items) == 0
    assert total == 0
    mock_wishlist_repo.get_by_user.assert_called_once_with(user_id, 10, 5)


@pytest.mark.asyncio
async def test_is_in_wishlist_true(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    user_id,
    course_id,
):
    mock_wishlist_repo.exists.return_value = True

    result = await wishlist_service.is_in_wishlist(user_id=user_id, course_id=course_id)

    assert result is True
    mock_wishlist_repo.exists.assert_called_once_with(user_id, course_id)


@pytest.mark.asyncio
async def test_is_in_wishlist_false(
    wishlist_service: WishlistService,
    mock_wishlist_repo: AsyncMock,
    user_id,
    course_id,
):
    mock_wishlist_repo.exists.return_value = False

    result = await wishlist_service.is_in_wishlist(user_id=user_id, course_id=course_id)

    assert result is False
