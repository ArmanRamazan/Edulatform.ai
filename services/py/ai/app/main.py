from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from common.errors import register_error_handlers
from common.logging import configure_logging
from common.rate_limit import RateLimitMiddleware
from app.config import Settings
from app.repositories.llm_client import GeminiClient
from app.repositories.cache import AICache
from app.services.ai_service import AIService
from app.services.tutor_service import TutorService
from app.services.credit_service import CreditService
from app.services.study_plan_service import StudyPlanService
from app.services.moderation_service import ModerationService
from app.services.strategist_service import StrategistService
from app.services.designer_service import DesignerService
from app.services.coach_service import CoachService
from app.services.orchestrator_service import AgentOrchestrator
from app.routes.ai import router as ai_router
from app.routes.coach_routes import router as coach_router
from app.routes.orchestrator_routes import router as orchestrator_router

app_settings = Settings()

_redis: Redis | None = None
_ai_service: AIService | None = None
_tutor_service: TutorService | None = None
_credit_service: CreditService | None = None
_study_plan_service: StudyPlanService | None = None
_moderation_service: ModerationService | None = None
_strategist_service: StrategistService | None = None
_designer_service: DesignerService | None = None
_coach_service: CoachService | None = None
_orchestrator_service: AgentOrchestrator | None = None
_http_client: httpx.AsyncClient | None = None


def get_ai_service() -> AIService:
    assert _ai_service is not None
    return _ai_service


def get_tutor_service() -> TutorService:
    assert _tutor_service is not None
    return _tutor_service


def get_credit_service() -> CreditService:
    assert _credit_service is not None
    return _credit_service


def get_study_plan_service() -> StudyPlanService:
    assert _study_plan_service is not None
    return _study_plan_service


def get_moderation_service() -> ModerationService:
    assert _moderation_service is not None
    return _moderation_service


def get_strategist_service() -> StrategistService:
    assert _strategist_service is not None
    return _strategist_service


def get_designer_service() -> DesignerService:
    assert _designer_service is not None
    return _designer_service


def get_coach_service() -> CoachService:
    assert _coach_service is not None
    return _coach_service


def get_orchestrator_service() -> AgentOrchestrator:
    assert _orchestrator_service is not None
    return _orchestrator_service


def _create_health_router() -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/health/ready")
    async def readiness() -> JSONResponse:
        checks: dict[str, str] = {}
        healthy = True

        if _redis is not None:
            try:
                await _redis.ping()
                checks["redis"] = "ok"
            except Exception:
                checks["redis"] = "unavailable"
                healthy = False

        has_key = bool(app_settings.gemini_api_key)
        checks["gemini_api_key"] = "configured" if has_key else "missing"
        if not has_key:
            healthy = False

        status_code = 200 if healthy else 503
        return JSONResponse(
            content={"status": "ok" if healthy else "degraded", "checks": checks},
            status_code=status_code,
        )

    return router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _redis, _ai_service, _tutor_service, _credit_service, _study_plan_service, _moderation_service, _strategist_service, _designer_service, _coach_service, _orchestrator_service, _http_client

    configure_logging(service_name="ai")
    logger = structlog.get_logger()

    _redis = Redis.from_url(app_settings.redis_url)
    _http_client = httpx.AsyncClient()

    llm = GeminiClient(_http_client, app_settings.gemini_api_key, app_settings.gemini_model)
    cache = AICache(_redis)
    _ai_service = AIService(llm, cache, app_settings)
    _tutor_service = TutorService(llm, cache, app_settings)
    _credit_service = CreditService(cache=cache)
    _study_plan_service = StudyPlanService(llm=llm, http_client=_http_client, settings=app_settings)
    _moderation_service = ModerationService(llm=llm)
    _strategist_service = StrategistService(
        gemini_client=llm, cache=cache, http_client=_http_client, settings=app_settings,
    )
    _designer_service = DesignerService(
        gemini_client=llm, cache=cache, http_client=_http_client, settings=app_settings,
    )
    _coach_service = CoachService(llm=llm, cache=cache, settings=app_settings)
    _orchestrator_service = AgentOrchestrator(
        strategist=_strategist_service,
        designer=_designer_service,
        cache=cache,
        http_client=_http_client,
        settings=app_settings,
    )

    logger.info("service_started", port=8006)
    yield

    await _http_client.aclose()
    await _redis.aclose()


app = FastAPI(title="AI Service", lifespan=lifespan)
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
app.include_router(ai_router)
app.include_router(coach_router)
app.include_router(orchestrator_router)
app.include_router(_create_health_router())

Instrumentator().instrument(app).expose(app)
