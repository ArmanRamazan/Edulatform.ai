from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from common.database import create_pool, update_pool_metrics
from common.errors import register_error_handlers
from common.health import create_health_router
from common.logging import configure_logging
from common.rate_limit import RateLimitMiddleware
from app.config import Settings
from app.repositories.user_repo import UserRepository
from app.repositories.token_repo import TokenRepository
from app.repositories.verification_repo import VerificationRepository
from app.repositories.password_reset_repo import PasswordResetRepository
from app.services.auth_service import AuthService
from app.routes.auth import router as auth_router
from app.routes.admin import router as admin_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    assert _auth_service is not None
    return _auth_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _auth_service

    configure_logging(service_name="identity")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_users.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_add_role.sql") as f:
            await conn.execute(f.read())
        with open("migrations/003_add_admin_role.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_refresh_tokens.sql") as f:
            await conn.execute(f.read())
        with open("migrations/005_email_verification.sql") as f:
            await conn.execute(f.read())
        with open("migrations/006_password_reset.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    repo = UserRepository(_pool)
    token_repo = TokenRepository(_pool)
    verification_repo = VerificationRepository(_pool)
    password_reset_repo = PasswordResetRepository(_pool)
    _auth_service = AuthService(
        repo=repo,
        jwt_secret=app_settings.jwt_secret,
        jwt_algorithm=app_settings.jwt_algorithm,
        jwt_ttl_seconds=app_settings.jwt_ttl_seconds,
        token_repo=token_repo,
        refresh_token_ttl_days=app_settings.refresh_token_ttl_days,
        verification_repo=verification_repo,
        password_reset_repo=password_reset_repo,
    )
    logger.info("service_started", port=8001)
    yield
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Identity Service", lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RateLimitMiddleware,
    redis_getter=lambda: _redis,
    limit=app_settings.rate_limit_per_minute,
    window=60,
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "identity")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
