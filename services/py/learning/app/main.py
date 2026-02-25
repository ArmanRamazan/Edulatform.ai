from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from common.database import create_pool, update_pool_metrics
from common.errors import register_error_handlers
from common.health import create_health_router
from common.rate_limit import RateLimitMiddleware
from app.config import Settings
from app.repositories.quiz_repo import QuizRepository
from app.repositories.flashcard_repo import FlashcardRepository
from app.services.quiz_service import QuizService
from app.services.flashcard_service import FlashcardService
from app.routes.quizzes import router as quizzes_router
from app.routes.flashcards import router as flashcards_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_quiz_service: QuizService | None = None
_flashcard_service: FlashcardService | None = None


def get_quiz_service() -> QuizService:
    assert _quiz_service is not None
    return _quiz_service


def get_flashcard_service() -> FlashcardService:
    assert _flashcard_service is not None
    return _flashcard_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _quiz_service, _flashcard_service

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_quizzes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_flashcards.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    quiz_repo = QuizRepository(_pool)
    _quiz_service = QuizService(quiz_repo)

    flashcard_repo = FlashcardRepository(_pool)
    _flashcard_service = FlashcardService(flashcard_repo)
    yield
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Learning Engine", lifespan=lifespan)
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
app.include_router(quizzes_router)
app.include_router(flashcards_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "learning")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
