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
from app.cache import CourseCache
from app.config import Settings
from app.repositories.bundle_repo import BundleRepository
from app.repositories.promotion_repo import PromotionRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.course_repo import CourseRepository
from app.repositories.module_repo import ModuleRepository
from app.repositories.lesson_repo import LessonRepository
from app.repositories.review_repo import ReviewRepository
from app.repositories.wishlist_repo import WishlistRepository
from app.services.bundle_service import BundleService
from app.services.promotion_service import PromotionService
from app.services.course_service import CourseService
from app.services.module_service import ModuleService
from app.services.lesson_service import LessonService
from app.services.review_service import ReviewService
from app.services.wishlist_service import WishlistService
from app.routes.bundles import router as bundles_router
from app.routes.promotions import router as promotions_router
from app.routes.categories import router as categories_router
from app.routes.courses import router as courses_router
from app.routes.modules import router as modules_router
from app.routes.lessons import router as lessons_router
from app.routes.analytics import router as analytics_router
from app.routes.reviews import router as reviews_router
from app.routes.wishlist_routes import router as wishlist_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_bundle_service: BundleService | None = None
_promotion_service: PromotionService | None = None
_course_service: CourseService | None = None
_module_service: ModuleService | None = None
_lesson_service: LessonService | None = None
_review_service: ReviewService | None = None
_wishlist_service: WishlistService | None = None
_category_repo: CategoryRepository | None = None


def get_bundle_service() -> BundleService:
    assert _bundle_service is not None
    return _bundle_service


def get_promotion_service() -> PromotionService:
    assert _promotion_service is not None
    return _promotion_service


def get_course_service() -> CourseService:
    assert _course_service is not None
    return _course_service


def get_module_service() -> ModuleService:
    assert _module_service is not None
    return _module_service


def get_lesson_service() -> LessonService:
    assert _lesson_service is not None
    return _lesson_service


def get_review_service() -> ReviewService:
    assert _review_service is not None
    return _review_service


def get_wishlist_service() -> WishlistService:
    assert _wishlist_service is not None
    return _wishlist_service


def get_category_repo() -> CategoryRepository:
    assert _category_repo is not None
    return _category_repo


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _bundle_service, _promotion_service, _course_service, _module_service, _lesson_service, _review_service, _wishlist_service, _category_repo

    configure_logging(service_name="course")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_courses.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_modules_lessons.sql") as f:
            await conn.execute(f.read())
        with open("migrations/003_reviews.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_search_index.sql") as f:
            await conn.execute(f.read())
        with open("migrations/005_indexes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/006_categories.sql") as f:
            await conn.execute(f.read())
        with open("migrations/007_analytics.sql") as f:
            await conn.execute(f.read())
        with open("migrations/008_bundles.sql") as f:
            await conn.execute(f.read())
        with open("migrations/009_promotions.sql") as f:
            await conn.execute(f.read())
        with open("migrations/010_wishlist.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)
    _cache = CourseCache(_redis)

    _category_repo = CategoryRepository(_pool)
    course_repo = CourseRepository(_pool)
    module_repo = ModuleRepository(_pool)
    lesson_repo = LessonRepository(_pool)
    review_repo = ReviewRepository(_pool)

    bundle_repo = BundleRepository(_pool)
    _bundle_service = BundleService(bundle_repo, course_repo)
    promotion_repo = PromotionRepository(_pool)
    _promotion_service = PromotionService(promotion_repo, course_repo)
    _course_service = CourseService(course_repo, module_repo, lesson_repo, cache=_cache)
    _module_service = ModuleService(module_repo, course_repo, cache=_cache)
    _lesson_service = LessonService(lesson_repo, module_repo, course_repo, cache=_cache)
    _review_service = ReviewService(review_repo, course_repo, cache=_cache)
    wishlist_repo = WishlistRepository(_pool)
    _wishlist_service = WishlistService(wishlist_repo, course_repo)
    logger.info("service_started", port=8002)
    yield
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Course Service", lifespan=lifespan)
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
app.include_router(analytics_router)
app.include_router(bundles_router)
app.include_router(promotions_router)
app.include_router(categories_router)
app.include_router(courses_router)
app.include_router(modules_router)
app.include_router(lessons_router)
app.include_router(reviews_router)
app.include_router(wishlist_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "course")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
