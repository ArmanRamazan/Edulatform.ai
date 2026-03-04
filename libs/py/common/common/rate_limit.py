from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


@dataclass(frozen=True)
class RateLimitConfig:
    """Configuration for per-route rate limiting.

    Attributes:
        key_type: How to derive the rate-limit key.
            - "ip": client IP (default)
            - "user": user_id extracted from JWT ``sub`` claim
            - "ip_and_user": ``{ip}:{user_id}``
        max_requests: Static request cap per window. Ignored when *dynamic_limit*
            returns a positive value.
        window_seconds: Sliding-window duration in seconds.
        exclude_roles: Roles that bypass rate limiting entirely.
            Matched against the ``role`` JWT claim.
        dynamic_limit: Optional callable ``(claims: dict) -> int`` that returns
            the effective limit for a given user.  Return ``0`` for unlimited.

    Example usage patterns::

        # Global IP-based
        Depends(rate_limit(RateLimitConfig(key_type="ip", max_requests=100, window_seconds=60)))

        # Per-user
        Depends(rate_limit(RateLimitConfig(key_type="user", max_requests=10, window_seconds=60)))

        # Dynamic per-tier
        def get_ai_limit(claims: dict) -> int:
            tier = claims.get("tier", "free")
            return {"free": 10, "student": 100}.get(tier, 0)

        Depends(rate_limit(RateLimitConfig(key_type="user", dynamic_limit=get_ai_limit)))
    """

    max_requests: int
    window_seconds: int
    key_type: str = "ip"
    exclude_roles: tuple[str, ...] = ()
    dynamic_limit: Callable[[dict], int] | None = None


class RateLimiter:
    """Low-level rate limiter backed by Redis INCR + EXPIRE."""

    def __init__(self, redis, limit: int, window_seconds: int) -> None:  # type: ignore[no-untyped-def]
        self._redis = redis
        self._limit = limit
        self._window = window_seconds

    async def check(self, key: str) -> bool:
        redis_key = f"rate:{key}"
        current = await self._redis.incr(redis_key)
        if current == 1:
            await self._redis.expire(redis_key, self._window)
        return current <= self._limit


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global middleware for IP-based rate limiting (backward-compatible)."""

    def __init__(self, app: ASGIApp, redis_getter: Callable, limit: int, window: int) -> None:
        super().__init__(app)
        self._redis_getter = redis_getter
        self._limit = limit
        self._window = window

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        redis = self._redis_getter()
        if redis is None:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        limiter = RateLimiter(redis, self._limit, self._window)
        if not await limiter.check(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(self._window)},
            )
        return await call_next(request)


def _extract_claims(request: Request, jwt_secret: str | None) -> dict:
    """Best-effort JWT claim extraction. Returns empty dict on failure."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or jwt_secret is None:
        return {}
    token = auth[7:]
    try:
        return jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return {}


def _build_key(config: RateLimitConfig, request: Request, claims: dict) -> str:
    """Build the Redis key based on config.key_type."""
    ip = request.client.host if request.client else "unknown"
    user_id = claims.get("sub", "")

    if config.key_type == "user":
        return user_id if user_id else ip
    if config.key_type == "ip_and_user":
        uid = user_id if user_id else "anon"
        return f"{ip}:{uid}"
    # default: ip
    return ip


def rate_limit(
    config: RateLimitConfig,
    *,
    redis_getter: Callable | None = None,
    jwt_secret: str | None = None,
) -> Callable:
    """FastAPI dependency factory for per-route rate limiting.

    Args:
        config: Rate limiting configuration.
        redis_getter: Callable returning a Redis instance (or ``None`` to skip).
            If not provided, the dependency silently skips rate limiting.
        jwt_secret: Secret used to decode JWT for user-based limiting.
            When ``None``, user extraction is attempted with a default
            ``"test-secret"`` for convenience in simple setups, but you
            should always provide the real secret in production.

    Returns:
        An async dependency compatible with ``fastapi.Depends()``.
    """

    async def _dependency(request: Request) -> None:
        redis = redis_getter() if redis_getter else None
        if redis is None:
            return

        # Determine the secret to use for JWT decoding
        secret = jwt_secret or "test-secret"

        # Extract claims for user-based features
        claims: dict = {}
        if config.key_type in ("user", "ip_and_user") or config.exclude_roles or config.dynamic_limit:
            claims = _extract_claims(request, secret)

        # Check role exclusion
        if config.exclude_roles and claims.get("role") in config.exclude_roles:
            return

        # Determine effective limit
        effective_limit = config.max_requests
        if config.dynamic_limit is not None and claims:
            effective_limit = config.dynamic_limit(claims)

        # 0 means unlimited
        if effective_limit == 0:
            return

        key = _build_key(config, request, claims)
        limiter = RateLimiter(redis, effective_limit, config.window_seconds)
        if not await limiter.check(key):
            from starlette.exceptions import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(config.window_seconds)},
            )

    return _dependency
