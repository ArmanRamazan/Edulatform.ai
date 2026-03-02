from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

import pytest

from common.errors import ForbiddenError
from app.repositories.cache import AICache
from app.services.credit_service import CreditService


@pytest.fixture
def mock_cache():
    return AsyncMock(spec=AICache)


@pytest.fixture
def credit_service(mock_cache):
    return CreditService(cache=mock_cache)


class TestGetLimit:
    def test_free_tier_limit(self, credit_service):
        assert credit_service.get_limit("free") == 10

    def test_student_tier_limit(self, credit_service):
        assert credit_service.get_limit("student") == 100

    def test_pro_tier_unlimited(self, credit_service):
        assert credit_service.get_limit("pro") == -1

    def test_unknown_tier_defaults_to_free(self, credit_service):
        assert credit_service.get_limit("unknown") == 10


class TestGetUsed:
    async def test_returns_cache_value(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 5
        result = await credit_service.get_used("user-1")
        assert result == 5
        mock_cache.get_credits_used.assert_called_once_with("user-1")


class TestCheckAndConsume:
    async def test_increments_and_returns_remaining(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 3
        mock_cache.increment_credits.return_value = 4
        remaining = await credit_service.check_and_consume("user-1", "free")
        assert remaining == 6  # limit 10 - used 4
        mock_cache.increment_credits.assert_called_once_with("user-1")

    async def test_at_limit_raises_forbidden(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 10  # at free limit
        with pytest.raises(ForbiddenError, match="AI credit limit reached"):
            await credit_service.check_and_consume("user-1", "free")
        mock_cache.increment_credits.assert_not_called()

    async def test_over_limit_raises_forbidden(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 100  # at student limit
        with pytest.raises(ForbiddenError, match="AI credit limit reached"):
            await credit_service.check_and_consume("user-1", "student")

    async def test_pro_tier_never_raises(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 99999
        mock_cache.increment_credits.return_value = 100000
        remaining = await credit_service.check_and_consume("user-1", "pro")
        assert remaining == 999999
        mock_cache.increment_credits.assert_called_once_with("user-1")

    async def test_student_tier_higher_limit(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 50
        mock_cache.increment_credits.return_value = 51
        remaining = await credit_service.check_and_consume("user-1", "student")
        assert remaining == 49  # limit 100 - used 51


class TestGetStatus:
    async def test_returns_correct_status_dict(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 3

        status = await credit_service.get_status("user-1", "free")

        assert status["used"] == 3
        assert status["limit"] == 10
        assert status["remaining"] == 7
        assert status["tier"] == "free"
        # reset_at should be next midnight UTC
        reset_at = datetime.fromisoformat(status["reset_at"])
        now = datetime.now(timezone.utc)
        expected = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert reset_at == expected

    async def test_pro_tier_status(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 500

        status = await credit_service.get_status("user-1", "pro")

        assert status["used"] == 500
        assert status["limit"] == -1
        assert status["remaining"] == 999999
        assert status["tier"] == "pro"

    async def test_student_tier_status(self, credit_service, mock_cache):
        mock_cache.get_credits_used.return_value = 0

        status = await credit_service.get_status("user-1", "student")

        assert status["used"] == 0
        assert status["limit"] == 100
        assert status["remaining"] == 100
        assert status["tier"] == "student"
