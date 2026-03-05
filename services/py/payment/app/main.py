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
from app.repositories.coupon_repo import CouponRepository
from app.services.payment_service import PaymentService
from app.services.earnings_service import EarningsService
from app.services.coupon_service import CouponService
from app.services.invoice_service import InvoiceService
from app.services.refund_service import RefundService
from app.repositories.refund_repo import RefundRepository
from app.repositories.gift_repo import GiftRepository
from app.adapters.invoice import InvoicePDFGenerator
from app.services.gift_service import GiftService
from app.services.org_subscription_service import OrgSubscriptionService
from app.repositories.org_subscription_repo import OrgSubscriptionRepository
from app.repositories.stripe_client import StripeClient
from app.routes.payments import router as payments_router
from app.routes.earnings import router as earnings_router
from app.routes.coupons import router as coupons_router
from app.routes.invoices import router as invoices_router
from app.routes.refunds import router as refunds_router
from app.routes.gifts import router as gifts_router
from app.routes.org_subscriptions import router as org_subscriptions_router

app_settings = Settings()

_pool: asyncpg.Pool | None = None
_redis: Redis | None = None
_payment_service: PaymentService | None = None
_earnings_service: EarningsService | None = None
_coupon_service: CouponService | None = None
_invoice_service: InvoiceService | None = None
_refund_service: RefundService | None = None
_gift_service: GiftService | None = None
_org_subscription_service: OrgSubscriptionService | None = None
_stripe_client: StripeClient | None = None


def get_payment_service() -> PaymentService:
    assert _payment_service is not None
    return _payment_service


def get_earnings_service() -> EarningsService:
    assert _earnings_service is not None
    return _earnings_service


def get_coupon_service() -> CouponService:
    assert _coupon_service is not None
    return _coupon_service


def get_invoice_service() -> InvoiceService:
    assert _invoice_service is not None
    return _invoice_service


def get_refund_service() -> RefundService:
    assert _refund_service is not None
    return _refund_service


def get_gift_service() -> GiftService:
    assert _gift_service is not None
    return _gift_service


def get_org_subscription_service() -> OrgSubscriptionService:
    assert _org_subscription_service is not None
    return _org_subscription_service


def get_stripe_client() -> StripeClient:
    assert _stripe_client is not None
    return _stripe_client


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    global _pool, _redis, _payment_service, _earnings_service, _coupon_service, _invoice_service, _refund_service, _gift_service, _org_subscription_service, _stripe_client

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
        with open("migrations/005_coupons.sql") as f:
            await conn.execute(f.read())
        with open("migrations/006_refunds.sql") as f:
            await conn.execute(f.read())
        with open("migrations/007_gifts.sql") as f:
            await conn.execute(f.read())
        with open("migrations/008_org_subscriptions.sql") as f:
            await conn.execute(f.read())

    _redis = Redis.from_url(app_settings.redis_url)

    repo = PaymentRepository(_pool)
    earnings_repo = EarningsRepository(_pool)
    coupon_repo = CouponRepository(_pool)
    _payment_service = PaymentService(repo, earnings_repo)
    _earnings_service = EarningsService(earnings_repo)
    _coupon_service = CouponService(coupon_repo)
    _invoice_service = InvoiceService(
        payment_repo=repo,
        pdf_generator=InvoicePDFGenerator(),
    )
    refund_repo = RefundRepository(_pool)
    _refund_service = RefundService(refund_repo=refund_repo, payment_repo=repo)
    gift_repo = GiftRepository(_pool)
    _gift_service = GiftService(gift_repo=gift_repo, payment_repo=repo)
    org_sub_repo = OrgSubscriptionRepository(_pool)
    _stripe_client = StripeClient(app_settings.stripe_secret_key)
    _org_subscription_service = OrgSubscriptionService(
        repo=org_sub_repo, stripe_client=_stripe_client,
    )
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
app.include_router(coupons_router)
app.include_router(invoices_router)
app.include_router(refunds_router)
app.include_router(gifts_router)
app.include_router(org_subscriptions_router)
app.include_router(create_health_router(lambda: _pool, lambda: _redis))


@app.middleware("http")
async def pool_metrics_middleware(request, call_next):  # type: ignore[no-untyped-def]
    if _pool is not None:
        update_pool_metrics(_pool, "payment")
    return await call_next(request)


Instrumentator().instrument(app).expose(app)
