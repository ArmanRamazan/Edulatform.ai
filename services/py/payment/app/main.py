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
from app.repositories.payment_repo import PaymentRepository
from app.repositories.earnings_repo import EarningsRepository
from app.services.payment_service import PaymentService
from app.services.earnings_service import EarningsService
from app.routes.payments import router as payments_router
from app.routes.earnings import router as earnings_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_payment_service: PaymentService | None = None
_earnings_service: EarningsService | None = None


def get_payment_service() -> PaymentService:
    assert _payment_service is not None
    return _payment_service


def get_earnings_service() -> EarningsService:
    assert _earnings_service is not None
    return _earnings_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _payment_service, _earnings_service

    configure_logging(service_name="payment")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_payments.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_indexes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/003_subscriptions.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_earnings_payouts.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    repo = PaymentRepository(_pool)
    earnings_repo = EarningsRepository(_pool)
    _payment_service = PaymentService(repo, earnings_repo)
    _earnings_service = EarningsService(earnings_repo)
    logger.info("service_started", port=8004)
    yield
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Payment Service", lifespan=lifespan)
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
app.include_router(payments_router)
app.include_router(earnings_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "payment")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
