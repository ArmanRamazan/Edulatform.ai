import asyncio

import stripe

from common.errors import AppError


class StripeClient:
    def __init__(self, secret_key: str) -> None:
        stripe.api_key = secret_key

    async def create_customer(self, email: str, name: str) -> str:
        try:
            customer = await asyncio.to_thread(
                stripe.Customer.create, email=email, name=name
            )
        except stripe.StripeError as e:
            raise AppError(str(e), status_code=502) from e
        return customer.id

    async def create_subscription(
        self, customer_id: str, price_id: str, payment_method_id: str
    ) -> dict:
        try:
            await asyncio.to_thread(
                stripe.PaymentMethod.attach,
                payment_method_id,
                customer=customer_id,
            )
            sub = await asyncio.to_thread(
                stripe.Subscription.create,
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
            )
        except stripe.StripeError as e:
            raise AppError(str(e), status_code=502) from e
        return {
            "id": sub.id,
            "status": sub.status,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
        }

    async def cancel_subscription(
        self, stripe_subscription_id: str, at_period_end: bool = True
    ) -> dict:
        try:
            if at_period_end:
                sub = await asyncio.to_thread(
                    stripe.Subscription.modify,
                    stripe_subscription_id,
                    cancel_at_period_end=True,
                )
                return {
                    "id": sub.id,
                    "status": sub.status,
                    "cancel_at_period_end": sub.cancel_at_period_end,
                }
            else:
                sub = await asyncio.to_thread(
                    stripe.Subscription.cancel, stripe_subscription_id
                )
                return {
                    "id": sub.id,
                    "status": sub.status,
                }
        except stripe.StripeError as e:
            raise AppError(str(e), status_code=502) from e

    async def construct_webhook_event(
        self, payload: bytes, sig_header: str, secret: str
    ) -> dict:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        except stripe.SignatureVerificationError as e:
            raise AppError(str(e), status_code=400) from e
        return event
