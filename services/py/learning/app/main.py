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
from app.repositories.quiz_repo import QuizRepository
from app.repositories.flashcard_repo import FlashcardRepository
from app.repositories.concept_repo import ConceptRepository
from app.repositories.streak_repo import StreakRepository
from app.repositories.leaderboard_repo import LeaderboardRepository
from app.repositories.discussion_repo import DiscussionRepository
from app.repositories.xp_repo import XpRepository
from app.repositories.badge_repo import BadgeRepository
from app.repositories.pretest_repo import PretestRepository
from app.repositories.velocity_repo import VelocityRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.study_group_repo import StudyGroupRepository
from app.services.quiz_service import QuizService
from app.services.flashcard_service import FlashcardService
from app.services.concept_service import ConceptService
from app.services.streak_service import StreakService
from app.services.leaderboard_service import LeaderboardService
from app.services.discussion_service import DiscussionService
from app.services.xp_service import XpService
from app.services.badge_service import BadgeService
from app.services.pretest_service import PretestService
from app.services.velocity_service import VelocityService
from app.services.activity_service import ActivityService
from app.services.study_group_service import StudyGroupService
from app.routes.quizzes import router as quizzes_router
from app.routes.flashcards import router as flashcards_router
from app.routes.concepts import router as concepts_router
from app.routes.streaks import router as streaks_router
from app.routes.leaderboard import router as leaderboard_router
from app.routes.discussions import router as discussions_router
from app.routes.xp import router as xp_router
from app.routes.badges import router as badges_router
from app.routes.pretests import router as pretests_router
from app.routes.velocity import router as velocity_router
from app.routes.activity import router as activity_router
from app.routes.study_groups import router as study_groups_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_quiz_service: QuizService | None = None
_flashcard_service: FlashcardService | None = None
_concept_service: ConceptService | None = None
_streak_service: StreakService | None = None
_leaderboard_service: LeaderboardService | None = None
_discussion_service: DiscussionService | None = None
_xp_service: XpService | None = None
_badge_service: BadgeService | None = None
_pretest_service: PretestService | None = None
_velocity_service: VelocityService | None = None
_activity_service: ActivityService | None = None
_study_group_service: StudyGroupService | None = None


def get_quiz_service() -> QuizService:
    assert _quiz_service is not None
    return _quiz_service


def get_flashcard_service() -> FlashcardService:
    assert _flashcard_service is not None
    return _flashcard_service


def get_concept_service() -> ConceptService:
    assert _concept_service is not None
    return _concept_service


def get_streak_service() -> StreakService:
    assert _streak_service is not None
    return _streak_service


def get_leaderboard_service() -> LeaderboardService:
    assert _leaderboard_service is not None
    return _leaderboard_service


def get_discussion_service() -> DiscussionService:
    assert _discussion_service is not None
    return _discussion_service


def get_xp_service() -> XpService:
    assert _xp_service is not None
    return _xp_service


def get_badge_service() -> BadgeService:
    assert _badge_service is not None
    return _badge_service


def get_pretest_service() -> PretestService:
    assert _pretest_service is not None
    return _pretest_service


def get_velocity_service() -> VelocityService:
    assert _velocity_service is not None
    return _velocity_service


def get_activity_service() -> ActivityService:
    assert _activity_service is not None
    return _activity_service


def get_study_group_service() -> StudyGroupService:
    assert _study_group_service is not None
    return _study_group_service


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _quiz_service, _flashcard_service, _concept_service, _streak_service, _leaderboard_service, _discussion_service, _xp_service, _badge_service, _pretest_service, _velocity_service, _activity_service, _study_group_service

    configure_logging(service_name="learning")
    logger = structlog.get_logger()

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
        with open("migrations/003_concepts.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_indexes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/005_streaks.sql") as f:
            await conn.execute(f.read())
        with open("migrations/006_leaderboard.sql") as f:
            await conn.execute(f.read())
        with open("migrations/007_discussions.sql") as f:
            await conn.execute(f.read())
        with open("migrations/008_xp_badges.sql") as f:
            await conn.execute(f.read())
        with open("migrations/009_pretests.sql") as f:
            await conn.execute(f.read())
        with open("migrations/010_activity_feed.sql") as f:
            await conn.execute(f.read())
        with open("migrations/011_study_groups.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    activity_repo = ActivityRepository(_pool)
    _activity_service = ActivityService(activity_repo)

    concept_repo = ConceptRepository(_pool)
    _concept_service = ConceptService(concept_repo, activity_service=_activity_service)

    quiz_repo = QuizRepository(_pool)
    flashcard_repo = FlashcardRepository(_pool)
    _quiz_service = QuizService(
        quiz_repo, concept_service=_concept_service, flashcard_repo=flashcard_repo,
        activity_service=_activity_service,
    )

    _flashcard_service = FlashcardService(flashcard_repo, activity_service=_activity_service)

    streak_repo = StreakRepository(_pool)
    _streak_service = StreakService(streak_repo, activity_service=_activity_service)

    leaderboard_repo = LeaderboardRepository(_pool)
    _leaderboard_service = LeaderboardService(leaderboard_repo)

    discussion_repo = DiscussionRepository(_pool)
    _discussion_service = DiscussionService(discussion_repo)

    xp_repo = XpRepository(_pool)
    _xp_service = XpService(xp_repo)

    badge_repo = BadgeRepository(_pool)
    _badge_service = BadgeService(badge_repo, activity_service=_activity_service)

    pretest_repo = PretestRepository(_pool)
    _pretest_service = PretestService(pretest_repo, concept_repo)

    velocity_repo = VelocityRepository(_pool)
    _velocity_service = VelocityService(velocity_repo)

    study_group_repo = StudyGroupRepository(_pool)
    _study_group_service = StudyGroupService(study_group_repo)

    logger.info("service_started", port=8007)
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
app.include_router(concepts_router)
app.include_router(streaks_router)
app.include_router(leaderboard_router)
app.include_router(discussions_router)
app.include_router(xp_router)
app.include_router(badges_router)
app.include_router(pretests_router)
app.include_router(velocity_router)
app.include_router(activity_router)
app.include_router(study_groups_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "learning")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
