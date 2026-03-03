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
from app.repositories.enrollment_repo import EnrollmentRepository
from app.repositories.progress_repo import ProgressRepository
from app.services.enrollment_service import EnrollmentService
from app.services.progress_service import ProgressService
from app.routes.enrollments import router as enrollments_router
from app.routes.progress import router as progress_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_enrollment_service: EnrollmentService | None = None
_progress_service: ProgressService | None = None


def get_enrollment_service() -> EnrollmentService:
    assert _enrollment_service is not None
    return _enrollment_service


def get_progress_service() -> ProgressService:
    assert _progress_service is not None
    return _progress_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _enrollment_service, _progress_service

    configure_logging(service_name="enrollment")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_enrollments.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_lesson_progress.sql") as f:
            await conn.execute(f.read())
        with open("migrations/003_indexes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_total_lessons.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    enrollment_repo = EnrollmentRepository(_pool)
    progress_repo = ProgressRepository(_pool)
    _enrollment_service = EnrollmentService(enrollment_repo)
    _progress_service = ProgressService(progress_repo, enrollment_repo=enrollment_repo)
    logger.info("service_started", port=8003)
    yield
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Enrollment Service", lifespan=lifespan)
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
app.include_router(enrollments_router)
app.include_router(progress_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "enrollment")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
