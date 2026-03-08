from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
import httpx
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from common.database import create_pool, update_pool_metrics
from common.errors import register_error_handlers
from common.health import create_health_router
from common.logging import configure_logging
from common.nats import NATSClient, create_nats_client
from common.rate_limit import RateLimitMiddleware
from app.config import Settings
from app.repositories.notification_repo import NotificationRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.adapters.email import EmailClient, StubEmailClient, ResendEmailClient
from app.adapters.slack_client import SlackClient, StubSlackClient, WebhookSlackClient
from app.adapters.ws_client import WsPublisher
from app.repositories.slack_config_repo import SlackConfigRepository
from app.services.notification_service import NotificationService
from app.services.smart_reminder_service import SmartReminderService
from app.services.messaging_service import MessagingService
from app.services.event_subscriber import NotificationEventSubscriber
from app.services.slack_reminder_service import SlackReminderService
from app.services.slack_search_service import SlackSearchService
from app.routes.notifications import router as notifications_router
from app.routes.messaging import router as messaging_router
from app.routes.slack import router as slack_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_notification_service: NotificationService | None = None
_smart_reminder_service: SmartReminderService | None = None
_messaging_service: MessagingService | None = None
_http_client: httpx.AsyncClient | None = None
_nats_client: NATSClient | None = None
_slack_reminder_service: SlackReminderService | None = None
_slack_search_service: SlackSearchService | None = None
_slack_config_repo: SlackConfigRepository | None = None


def get_notification_service() -> NotificationService:
    assert _notification_service is not None
    return _notification_service


def get_smart_reminder_service() -> SmartReminderService:
    assert _smart_reminder_service is not None
    return _smart_reminder_service


def get_messaging_service() -> MessagingService:
    assert _messaging_service is not None
    return _messaging_service


def get_slack_reminder_service() -> SlackReminderService:
    assert _slack_reminder_service is not None
    return _slack_reminder_service


def get_slack_search_service() -> SlackSearchService:
    assert _slack_search_service is not None
    return _slack_search_service


def get_slack_config_repo() -> SlackConfigRepository:
    assert _slack_config_repo is not None
    return _slack_config_repo


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _notification_service, _smart_reminder_service, _messaging_service, _http_client, _nats_client, _slack_reminder_service, _slack_search_service, _slack_config_repo

    configure_logging(service_name="notification")
    logger = structlog.get_logger()

    _pool = await create_pool(
        app_settings.database_url,
        min_size=app_settings.db_pool_min_size,
        max_size=app_settings.db_pool_max_size,
    )

    async with _pool.acquire() as conn:
        with open("migrations/001_notifications.sql") as f:
            await conn.execute(f.read())
        with open("migrations/002_indexes.sql") as f:
            await conn.execute(f.read())
        with open("migrations/003_streak_reminder_type.sql") as f:
            await conn.execute(f.read())
        with open("migrations/004_flashcard_reminder_type.sql") as f:
            await conn.execute(f.read())
        with open("migrations/005_conversations.sql") as f:
            await conn.execute(f.read())
        with open("migrations/006_messages.sql") as f:
            await conn.execute(f.read())
        with open("migrations/007_email_sent.sql") as f:
            await conn.execute(f.read())
        with open("migrations/008_org_id.sql") as f:
            await conn.execute(f.read())
        with open("migrations/009_event_id.sql") as f:
            await conn.execute(f.read())
        with open("migrations/010_slack_configs.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)
    _http_client = httpx.AsyncClient()

    repo = NotificationRepository(_pool)
    email_client: EmailClient
    if app_settings.resend_api_key:
        email_client = ResendEmailClient(
            api_key=app_settings.resend_api_key,
            http_client=_http_client,
            from_address=app_settings.email_from_address,
        )
        logger.info("email_client_initialized", type="resend")
    else:
        email_client = StubEmailClient()
        logger.info("email_client_initialized", type="stub")
    ws_publisher = WsPublisher(
        http_client=_http_client,
        ws_gateway_url=app_settings.ws_gateway_url,
    )

    _notification_service = NotificationService(
        repo, email_adapter=email_client, ws_publisher=ws_publisher,
    )

    conversation_repo = ConversationRepository(_pool)
    message_repo = MessageRepository(_pool)
    _messaging_service = MessagingService(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        ws_publisher=ws_publisher,
    )

    _smart_reminder_service = SmartReminderService(
        repo=repo,
        http_client=_http_client,
        learning_service_url=app_settings.learning_service_url,
        jwt_secret=app_settings.jwt_secret,
    )

    _slack_config_repo = SlackConfigRepository(_pool)

    slack_client: SlackClient
    if app_settings.slack_webhook_url:
        slack_client = WebhookSlackClient(http_client=_http_client)
        logger.info("slack_client_initialized", type="webhook")
    else:
        slack_client = StubSlackClient()
        logger.info("slack_client_initialized", type="stub")

    _slack_reminder_service = SlackReminderService(
        slack_config_repo=_slack_config_repo,
        slack_client=slack_client,
        ai_service_url=app_settings.ai_service_url,
        http_client=_http_client,
        jwt_secret=app_settings.jwt_secret,
    )

    _slack_search_service = SlackSearchService(
        http_client=_http_client,
        ai_service_url=app_settings.ai_service_url,
        jwt_secret=app_settings.jwt_secret,
    )

    _nats_client = create_nats_client(app_settings.nats_url)
    await _nats_client.connect()
    await _nats_client.ensure_stream(name="PLATFORM_EVENTS", subjects=["platform.>"])
    _event_subscriber = NotificationEventSubscriber(_nats_client, _notification_service)
    await _event_subscriber.start()
    logger.info("nats_subscriber_started")

    logger.info("service_started", port=8005)
    yield
    await _nats_client.close()
    await _http_client.aclose()
    await _redis.aclose()
    await _pool.close()


app = FastAPI(title="Notification Service", lifespan=lifespan)
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
app.include_router(notifications_router)
app.include_router(messaging_router)
app.include_router(slack_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "notification")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
