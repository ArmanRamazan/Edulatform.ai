import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

from common.errors import ForbiddenError, NotFoundError, AppError
from app.domain.coupon import Coupon, CouponUsage, DiscountType
from app.repositories.coupon_repo import CouponRepository
from app.services.coupon_service import CouponService


@pytest.fixture
def admin_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def course_id():
    return uuid4()


@pytest.fixture
def mock_coupon_repo():
    return AsyncMock(spec=CouponRepository)


@pytest.fixture
def coupon_service(mock_coupon_repo):
    return CouponService(repo=mock_coupon_repo)


@pytest.fixture
def sample_coupon(admin_id, course_id):
    return Coupon(
        id=uuid4(),
        code="SAVE20",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("20"),
        max_uses=100,
        current_uses=5,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        course_id=None,
        created_by=admin_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def fixed_coupon(admin_id, course_id):
    return Coupon(
        id=uuid4(),
        code="FLAT15",
        discount_type=DiscountType.FIXED,
        discount_value=Decimal("15"),
        max_uses=None,
        current_uses=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        course_id=course_id,
        created_by=admin_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def expired_coupon(admin_id):
    return Coupon(
        id=uuid4(),
        code="EXPIRED",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("10"),
        max_uses=None,
        current_uses=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=30),
        valid_until=datetime.now(timezone.utc) - timedelta(days=1),
        course_id=None,
        created_by=admin_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def maxed_coupon(admin_id):
    return Coupon(
        id=uuid4(),
        code="MAXED",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=Decimal("10"),
        max_uses=5,
        current_uses=5,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_until=datetime.now(timezone.utc) + timedelta(days=30),
        course_id=None,
        created_by=admin_id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


class TestCreateCoupon:
    async def test_create_coupon_admin(self, coupon_service, mock_coupon_repo, admin_id, sample_coupon):
        mock_coupon_repo.create_coupon.return_value = sample_coupon

        result = await coupon_service.create_coupon(
            admin_id=admin_id,
            role="admin",
            code="SAVE20",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("20"),
            max_uses=100,
            valid_from=sample_coupon.valid_from,
            valid_until=sample_coupon.valid_until,
            course_id=None,
        )

        assert result.code == "SAVE20"
        mock_coupon_repo.create_coupon.assert_awaited_once()

    async def test_create_coupon_non_admin(self, coupon_service, user_id):
        with pytest.raises(ForbiddenError):
            await coupon_service.create_coupon(
                admin_id=user_id,
                role="student",
                code="SAVE20",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("20"),
                max_uses=None,
                valid_from=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(days=30),
                course_id=None,
            )

    async def test_create_coupon_invalid_code(self, coupon_service, admin_id):
        with pytest.raises(AppError):
            await coupon_service.create_coupon(
                admin_id=admin_id,
                role="admin",
                code="bad code!",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("20"),
                max_uses=None,
                valid_from=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(days=30),
                course_id=None,
            )

    async def test_create_coupon_percentage_over_100(self, coupon_service, admin_id):
        with pytest.raises(AppError):
            await coupon_service.create_coupon(
                admin_id=admin_id,
                role="admin",
                code="TOOMUCH",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=Decimal("150"),
                max_uses=None,
                valid_from=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(days=30),
                course_id=None,
            )

    async def test_create_coupon_invalid_dates(self, coupon_service, admin_id):
        with pytest.raises(AppError):
            await coupon_service.create_coupon(
                admin_id=admin_id,
                role="admin",
                code="BADDATE",
                discount_type=DiscountType.FIXED,
                discount_value=Decimal("10"),
                max_uses=None,
                valid_from=datetime.now(timezone.utc) + timedelta(days=30),
                valid_until=datetime.now(timezone.utc),
                course_id=None,
            )


class TestValidateCoupon:
    async def test_validate_percentage(self, coupon_service, mock_coupon_repo, sample_coupon, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = sample_coupon
        mock_coupon_repo.has_user_used.return_value = False

        result = await coupon_service.validate_coupon(
            code="SAVE20",
            course_id=course_id,
            user_id=user_id,
            original_price=Decimal("100"),
        )

        assert result.original_price == Decimal("100")
        assert result.discount_amount == Decimal("20")
        assert result.final_price == Decimal("80")
        assert result.coupon_code == "SAVE20"

    async def test_validate_fixed(self, coupon_service, mock_coupon_repo, fixed_coupon, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = fixed_coupon
        mock_coupon_repo.has_user_used.return_value = False

        result = await coupon_service.validate_coupon(
            code="FLAT15",
            course_id=course_id,
            user_id=user_id,
            original_price=Decimal("100"),
        )

        assert result.original_price == Decimal("100")
        assert result.discount_amount == Decimal("15")
        assert result.final_price == Decimal("85")

    async def test_validate_fixed_capped_at_price(self, coupon_service, mock_coupon_repo, user_id, course_id, admin_id):
        big_fixed = Coupon(
            id=uuid4(),
            code="BIG50",
            discount_type=DiscountType.FIXED,
            discount_value=Decimal("50"),
            max_uses=None,
            current_uses=0,
            valid_from=datetime.now(timezone.utc) - timedelta(days=1),
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
            course_id=None,
            created_by=admin_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        mock_coupon_repo.get_coupon_by_code.return_value = big_fixed
        mock_coupon_repo.has_user_used.return_value = False

        result = await coupon_service.validate_coupon(
            code="BIG50",
            course_id=course_id,
            user_id=user_id,
            original_price=Decimal("30"),
        )

        assert result.discount_amount == Decimal("30")
        assert result.final_price == Decimal("0")

    async def test_validate_expired(self, coupon_service, mock_coupon_repo, expired_coupon, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = expired_coupon

        with pytest.raises(NotFoundError):
            await coupon_service.validate_coupon(
                code="EXPIRED",
                course_id=course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )

    async def test_validate_maxed_out(self, coupon_service, mock_coupon_repo, maxed_coupon, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = maxed_coupon

        with pytest.raises(NotFoundError):
            await coupon_service.validate_coupon(
                code="MAXED",
                course_id=course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )

    async def test_validate_wrong_course(self, coupon_service, mock_coupon_repo, fixed_coupon, user_id):
        mock_coupon_repo.get_coupon_by_code.return_value = fixed_coupon

        wrong_course_id = uuid4()
        with pytest.raises(NotFoundError):
            await coupon_service.validate_coupon(
                code="FLAT15",
                course_id=wrong_course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )

    async def test_validate_already_used(self, coupon_service, mock_coupon_repo, sample_coupon, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = sample_coupon
        mock_coupon_repo.has_user_used.return_value = True

        with pytest.raises(AppError) as exc_info:
            await coupon_service.validate_coupon(
                code="SAVE20",
                course_id=course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )
        assert exc_info.value.status_code == 400

    async def test_validate_all_courses(self, coupon_service, mock_coupon_repo, sample_coupon, user_id):
        mock_coupon_repo.get_coupon_by_code.return_value = sample_coupon
        mock_coupon_repo.has_user_used.return_value = False

        any_course = uuid4()
        result = await coupon_service.validate_coupon(
            code="SAVE20",
            course_id=any_course,
            user_id=user_id,
            original_price=Decimal("100"),
        )

        assert result.final_price == Decimal("80")

    async def test_validate_not_found(self, coupon_service, mock_coupon_repo, user_id, course_id):
        mock_coupon_repo.get_coupon_by_code.return_value = None

        with pytest.raises(NotFoundError):
            await coupon_service.validate_coupon(
                code="NONEXISTENT",
                course_id=course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )

    async def test_validate_inactive(self, coupon_service, mock_coupon_repo, user_id, course_id, admin_id):
        inactive = Coupon(
            id=uuid4(),
            code="INACTIVE",
            discount_type=DiscountType.PERCENTAGE,
            discount_value=Decimal("10"),
            max_uses=None,
            current_uses=0,
            valid_from=datetime.now(timezone.utc) - timedelta(days=1),
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
            course_id=None,
            created_by=admin_id,
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        mock_coupon_repo.get_coupon_by_code.return_value = inactive

        with pytest.raises(NotFoundError):
            await coupon_service.validate_coupon(
                code="INACTIVE",
                course_id=course_id,
                user_id=user_id,
                original_price=Decimal("100"),
            )


class TestApplyCoupon:
    async def test_apply_coupon(self, coupon_service, mock_coupon_repo, sample_coupon, user_id):
        payment_id = uuid4()
        mock_coupon_repo.get_coupon_by_code.return_value = sample_coupon

        await coupon_service.apply_coupon(
            code="SAVE20",
            user_id=user_id,
            payment_id=payment_id,
        )

        mock_coupon_repo.increment_usage.assert_awaited_once_with(sample_coupon.id)
        mock_coupon_repo.record_usage.assert_awaited_once_with(sample_coupon.id, user_id, payment_id)


class TestDeactivateCoupon:
    async def test_deactivate_admin(self, coupon_service, mock_coupon_repo, sample_coupon):
        mock_coupon_repo.deactivate_coupon.return_value = True

        await coupon_service.deactivate_coupon(
            admin_id=uuid4(),
            role="admin",
            coupon_id=sample_coupon.id,
        )

        mock_coupon_repo.deactivate_coupon.assert_awaited_once_with(sample_coupon.id)

    async def test_deactivate_non_admin(self, coupon_service, sample_coupon):
        with pytest.raises(ForbiddenError):
            await coupon_service.deactivate_coupon(
                admin_id=uuid4(),
                role="student",
                coupon_id=sample_coupon.id,
            )

    async def test_deactivate_not_found(self, coupon_service, mock_coupon_repo):
        mock_coupon_repo.deactivate_coupon.return_value = False

        with pytest.raises(NotFoundError):
            await coupon_service.deactivate_coupon(
                admin_id=uuid4(),
                role="admin",
                coupon_id=uuid4(),
            )


class TestListCoupons:
    async def test_list_coupons_admin(self, coupon_service, mock_coupon_repo, sample_coupon):
        mock_coupon_repo.list_coupons.return_value = ([sample_coupon], 1)

        items, total = await coupon_service.list_coupons(
            role="admin", limit=20, offset=0,
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].code == "SAVE20"

    async def test_list_coupons_non_admin(self, coupon_service):
        with pytest.raises(ForbiddenError):
            await coupon_service.list_coupons(role="student", limit=20, offset=0)
