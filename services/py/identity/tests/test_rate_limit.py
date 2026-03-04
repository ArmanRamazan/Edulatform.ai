import pytest
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI, Request, Header, Depends
from fastapi.responses import JSONResponse
from typing import Annotated

from common.rate_limit import (
    RateLimiter,
    RateLimitMiddleware,
    RateLimitConfig,
    rate_limit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counters: dict[str, int] = {}


def _counter(key: str) -> int:
    _counters[key] = _counters.get(key, 0) + 1
    return _counters[key]


@pytest.fixture(autouse=True)
def reset_counters():
    _counters.clear()


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=lambda key: _counter(key))
    redis.expire = AsyncMock()
    return redis


# ---------------------------------------------------------------------------
# Backward-compatible: existing RateLimiter API still works
# ---------------------------------------------------------------------------


async def test_rate_limiter_allows_under_limit(mock_redis):
    limiter = RateLimiter(mock_redis, limit=3, window_seconds=60)
    assert await limiter.check("test-ip") is True
    assert await limiter.check("test-ip") is True
    assert await limiter.check("test-ip") is True


async def test_rate_limiter_blocks_over_limit(mock_redis):
    limiter = RateLimiter(mock_redis, limit=2, window_seconds=60)
    assert await limiter.check("test-ip") is True
    assert await limiter.check("test-ip") is True
    assert await limiter.check("test-ip") is False


async def test_rate_limit_middleware_returns_429():
    call_count = 0

    async def mock_incr(key: str) -> int:
        nonlocal call_count
        call_count += 1
        return call_count

    redis = AsyncMock()
    redis.incr = mock_incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, redis_getter=lambda: redis, limit=2, window=60)

    @test_app.get("/test")
    async def test_endpoint() -> dict[str, str]:
        return {"ok": "true"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        resp1 = await client.get("/test")
        assert resp1.status_code == 200
        resp2 = await client.get("/test")
        assert resp2.status_code == 200
        resp3 = await client.get("/test")
        assert resp3.status_code == 429
        assert resp3.json()["detail"] == "Too many requests"
        assert "Retry-After" in resp3.headers


# ---------------------------------------------------------------------------
# RateLimitConfig defaults
# ---------------------------------------------------------------------------


def test_rate_limit_config_defaults():
    cfg = RateLimitConfig(max_requests=100, window_seconds=60)
    assert cfg.key_type == "ip"
    assert cfg.max_requests == 100
    assert cfg.window_seconds == 60
    assert cfg.exclude_roles == ()
    assert cfg.dynamic_limit is None


def test_rate_limit_config_frozen():
    cfg = RateLimitConfig(max_requests=10, window_seconds=60)
    with pytest.raises(AttributeError):
        cfg.max_requests = 20  # type: ignore[misc]


# ---------------------------------------------------------------------------
# IP-based rate limiting via rate_limit() dependency
# ---------------------------------------------------------------------------


async def test_rate_limit_ip_based():
    """rate_limit dependency with key_type='ip' uses client IP as key."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="ip", max_requests=2, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        assert (await client.get("/test")).status_code == 200
        assert (await client.get("/test")).status_code == 200
        assert (await client.get("/test")).status_code == 429


# ---------------------------------------------------------------------------
# User-based rate limiting
# ---------------------------------------------------------------------------


async def test_rate_limit_user_based():
    """rate_limit with key_type='user' uses user_id from JWT as key."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="user", max_requests=2, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    token = create_access_token("user-123", secret="test-secret")

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {token}"}
        assert (await client.get("/test", headers=headers)).status_code == 200
        assert (await client.get("/test", headers=headers)).status_code == 200
        resp = await client.get("/test", headers=headers)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


async def test_rate_limit_user_based_no_token_falls_back_to_ip():
    """If key_type='user' but no JWT present, fall back to IP-based key."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="user", max_requests=1, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        assert (await client.get("/test")).status_code == 200
        assert (await client.get("/test")).status_code == 429


# ---------------------------------------------------------------------------
# IP + User combined key
# ---------------------------------------------------------------------------


async def test_rate_limit_ip_and_user():
    """key_type='ip_and_user' combines IP and user_id."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="ip_and_user", max_requests=1, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    token = create_access_token("user-456", secret="test-secret")

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {token}"}
        assert (await client.get("/test", headers=headers)).status_code == 200
        assert (await client.get("/test", headers=headers)).status_code == 429

    # Verify the key contains both ip and user parts
    keys = list(_counts.keys())
    assert any("user-456" in k for k in keys)


# ---------------------------------------------------------------------------
# Dynamic limits
# ---------------------------------------------------------------------------


async def test_rate_limit_dynamic_limit():
    """dynamic_limit callable overrides max_requests based on user claims."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    def get_limit(claims: dict) -> int:
        tier = claims.get("tier", "free")
        if tier == "pro":
            return 0  # 0 means unlimited
        if tier == "student":
            return 100
        return 2  # free

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="user", max_requests=10, window_seconds=60, dynamic_limit=get_limit)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis, jwt_secret="test-secret"))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    # Free user: limit=2
    free_token = create_access_token("free-user", secret="test-secret", extra_claims={"tier": "free"})

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {free_token}"}
        assert (await client.get("/test", headers=headers)).status_code == 200
        assert (await client.get("/test", headers=headers)).status_code == 200
        assert (await client.get("/test", headers=headers)).status_code == 429


async def test_rate_limit_dynamic_limit_pro_unlimited():
    """dynamic_limit returning 0 means unlimited (no rate limiting)."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    def get_limit(claims: dict) -> int:
        return 0 if claims.get("tier") == "pro" else 1

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="user", max_requests=1, window_seconds=60, dynamic_limit=get_limit)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis, jwt_secret="test-secret"))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    pro_token = create_access_token("pro-user", secret="test-secret", extra_claims={"tier": "pro"})

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {pro_token}"}
        # Pro user should never be rate limited
        for _ in range(10):
            resp = await client.get("/test", headers=headers)
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Admin bypass (exclude_roles)
# ---------------------------------------------------------------------------


async def test_rate_limit_admin_bypass():
    """Users with excluded roles bypass rate limiting entirely."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(
        key_type="user", max_requests=1, window_seconds=60, exclude_roles=("admin",)
    )

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis, jwt_secret="test-secret"))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    admin_token = create_access_token("admin-1", secret="test-secret", extra_claims={"role": "admin"})

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {admin_token}"}
        for _ in range(5):
            assert (await client.get("/test", headers=headers)).status_code == 200


async def test_rate_limit_non_excluded_role_still_limited():
    """Non-excluded roles are still rate limited."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(
        key_type="user", max_requests=1, window_seconds=60, exclude_roles=("admin",)
    )

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis, jwt_secret="test-secret"))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    student_token = create_access_token("student-1", secret="test-secret", extra_claims={"role": "student"})

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        headers = {"Authorization": f"Bearer {student_token}"}
        assert (await client.get("/test", headers=headers)).status_code == 200
        assert (await client.get("/test", headers=headers)).status_code == 429


# ---------------------------------------------------------------------------
# 429 response contains Retry-After header
# ---------------------------------------------------------------------------


async def test_rate_limit_429_has_retry_after():
    """429 response includes Retry-After header with window seconds."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="ip", max_requests=1, window_seconds=120)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        await client.get("/test")
        resp = await client.get("/test")
        assert resp.status_code == 429
        assert resp.headers["Retry-After"] == "120"
        assert resp.json()["detail"] == "Too many requests"


# ---------------------------------------------------------------------------
# Redis unavailable — requests pass through
# ---------------------------------------------------------------------------


async def test_rate_limit_redis_none_passes_through():
    """If redis is None, rate limiting is skipped."""
    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="ip", max_requests=1, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: None))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        for _ in range(5):
            assert (await client.get("/test")).status_code == 200


# ---------------------------------------------------------------------------
# Different users have separate rate limit buckets
# ---------------------------------------------------------------------------


async def test_rate_limit_separate_buckets_per_user():
    """Different user_ids have independent rate limit counters."""
    _counts: dict[str, int] = {}

    async def _incr(key: str) -> int:
        _counts[key] = _counts.get(key, 0) + 1
        return _counts[key]

    redis = AsyncMock()
    redis.incr = _incr
    redis.expire = AsyncMock()

    test_app = FastAPI()
    cfg = RateLimitConfig(key_type="user", max_requests=1, window_seconds=60)

    @test_app.get("/test", dependencies=[Depends(rate_limit(cfg, redis_getter=lambda: redis))])
    async def endpoint() -> dict[str, str]:
        return {"ok": "true"}

    from common.security import create_access_token

    token_a = create_access_token("user-a", secret="test-secret")
    token_b = create_access_token("user-b", secret="test-secret")

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # User A: 1 allowed, then blocked
        assert (await client.get("/test", headers={"Authorization": f"Bearer {token_a}"})).status_code == 200
        assert (await client.get("/test", headers={"Authorization": f"Bearer {token_a}"})).status_code == 429

        # User B: still has their own quota
        assert (await client.get("/test", headers={"Authorization": f"Bearer {token_b}"})).status_code == 200
        assert (await client.get("/test", headers={"Authorization": f"Bearer {token_b}"})).status_code == 429
