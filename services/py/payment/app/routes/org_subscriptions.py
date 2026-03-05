from __future__ import annotations

from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, Header, Request

from common.errors import AppError, ForbiddenError
from app.domain.org_subscription import (
    OrgSubscription,
    OrgSubscriptionCreateRequest,
    OrgSubscriptionResponse,
)
from app.services.org_subscription_service import OrgSubscriptionService

router = APIRouter(tags=["org-subscriptions"])


def _get_org_sub_service() -> OrgSubscriptionService:
    from app.main import get_org_subscription_service
    return get_org_subscription_service()


def _get_current_user_claims(authorization: Annotated[str, Header()]) -> dict:
    from app.main import app_settings

    if not authorization.startswith("Bearer "):
        raise AppError("Invalid authorization header", status_code=401)
    token = authorization[7:]
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret, algorithms=[app_settings.jwt_algorithm]
        )
        return {
            "user_id": UUID(payload["sub"]),
            "role": payload.get("role", "student"),
            "is_verified": payload.get("is_verified", False),
            "organization_id": payload.get("organization_id"),
        }
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc


def _require_org_access(claims: dict, org_id: UUID) -> None:
    claim_org = claims.get("organization_id")
    if claim_org is None:
        raise ForbiddenError("No organization associated with this account")
    if UUID(claim_org) != org_id:
        raise ForbiddenError("Access denied to this organization")


def _to_response(sub: OrgSubscription) -> OrgSubscriptionResponse:
    return OrgSubscriptionResponse(
        id=sub.id,
        organization_id=sub.organization_id,
        plan_tier=sub.plan_tier.value,
        max_seats=sub.max_seats,
        current_seats=sub.current_seats,
        price_cents=sub.price_cents,
        status=sub.status.value,
        trial_ends_at=sub.trial_ends_at,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        created_at=sub.created_at,
    )


@router.post("/org-subscriptions", response_model=OrgSubscriptionResponse, status_code=201)
async def create_org_subscription(
    body: OrgSubscriptionCreateRequest,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[OrgSubscriptionService, Depends(_get_org_sub_service)],
) -> OrgSubscriptionResponse:
    claim_org = claims.get("organization_id")
    if claim_org is None:
        raise ForbiddenError("No organization associated with this account")

    sub = await service.create_subscription(
        organization_id=UUID(claim_org),
        plan_tier=body.plan_tier,
        payment_method_id=body.payment_method_id,
        org_email=body.org_email,
        org_name=body.org_name,
    )
    return _to_response(sub)


@router.get("/org-subscriptions/{org_id}", response_model=OrgSubscriptionResponse)
async def get_org_subscription(
    org_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[OrgSubscriptionService, Depends(_get_org_sub_service)],
) -> OrgSubscriptionResponse:
    _require_org_access(claims, org_id)
    sub = await service.get_subscription(org_id)
    return _to_response(sub)


@router.post("/org-subscriptions/{org_id}/cancel", response_model=OrgSubscriptionResponse)
async def cancel_org_subscription(
    org_id: UUID,
    claims: Annotated[dict, Depends(_get_current_user_claims)],
    service: Annotated[OrgSubscriptionService, Depends(_get_org_sub_service)],
) -> OrgSubscriptionResponse:
    _require_org_access(claims, org_id)
    sub = await service.cancel_subscription(org_id)
    return _to_response(sub)


@router.post("/webhooks/stripe-org")
async def stripe_org_webhook(request: Request) -> dict:
    from app.main import app_settings, get_stripe_client

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    stripe_client = get_stripe_client()
    event = await stripe_client.construct_webhook_event(
        payload, sig_header, app_settings.stripe_webhook_secret,
    )

    event_type = event["type"]
    data_object = event.get("data", {}).get("object", {})
    stripe_subscription_id = data_object.get("subscription")

    if stripe_subscription_id:
        service = _get_org_sub_service()
        await service.handle_webhook(
            event_type=event_type,
            stripe_subscription_id=stripe_subscription_id,
        )

    return {"status": "ok"}
