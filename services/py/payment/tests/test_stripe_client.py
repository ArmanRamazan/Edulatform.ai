import asyncio
from unittest.mock import MagicMock, patch

import pytest
import stripe

from app.repositories.stripe_client import StripeClient
from common.errors import AppError


@pytest.fixture
def client() -> StripeClient:
    return StripeClient(secret_key="sk_test_fake")


class TestCreateCustomer:
    async def test_returns_customer_id(self, client: StripeClient) -> None:
        mock_customer = MagicMock()
        mock_customer.id = "cus_abc123"

        with patch("stripe.Customer.create", return_value=mock_customer) as mock_create:
            result = await client.create_customer(
                email="user@example.com", name="Test User"
            )

        assert result == "cus_abc123"
        mock_create.assert_called_once_with(email="user@example.com", name="Test User")

    async def test_stripe_error_raises_app_error_502(self, client: StripeClient) -> None:
        with patch(
            "stripe.Customer.create",
            side_effect=stripe.StripeError("Connection failed"),
        ):
            with pytest.raises(AppError) as exc_info:
                await client.create_customer(email="user@example.com", name="Test User")

        assert exc_info.value.status_code == 502
        assert "Connection failed" in exc_info.value.message


class TestCreateSubscription:
    async def test_attaches_payment_method_and_creates_subscription(
        self, client: StripeClient
    ) -> None:
        mock_sub = MagicMock()
        mock_sub.id = "sub_xyz789"
        mock_sub.status = "active"
        mock_sub.current_period_start = 1700000000
        mock_sub.current_period_end = 1702592000

        with (
            patch("stripe.PaymentMethod.attach") as mock_attach,
            patch("stripe.Subscription.create", return_value=mock_sub) as mock_create,
        ):
            result = await client.create_subscription(
                customer_id="cus_abc123",
                price_id="price_monthly",
                payment_method_id="pm_card_visa",
            )

        mock_attach.assert_called_once_with(
            "pm_card_visa", customer="cus_abc123"
        )
        mock_create.assert_called_once_with(
            customer="cus_abc123",
            items=[{"price": "price_monthly"}],
            default_payment_method="pm_card_visa",
        )
        assert result == {
            "id": "sub_xyz789",
            "status": "active",
            "current_period_start": 1700000000,
            "current_period_end": 1702592000,
        }

    async def test_stripe_error_raises_app_error_502(self, client: StripeClient) -> None:
        with patch(
            "stripe.PaymentMethod.attach",
            side_effect=stripe.StripeError("Card declined"),
        ):
            with pytest.raises(AppError) as exc_info:
                await client.create_subscription(
                    customer_id="cus_abc123",
                    price_id="price_monthly",
                    payment_method_id="pm_card_visa",
                )

        assert exc_info.value.status_code == 502
        assert "Card declined" in exc_info.value.message


class TestCancelSubscription:
    async def test_cancels_at_period_end(self, client: StripeClient) -> None:
        mock_sub = MagicMock()
        mock_sub.id = "sub_xyz789"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = True

        with patch("stripe.Subscription.modify", return_value=mock_sub) as mock_modify:
            result = await client.cancel_subscription("sub_xyz789", at_period_end=True)

        mock_modify.assert_called_once_with(
            "sub_xyz789", cancel_at_period_end=True
        )
        assert result == {
            "id": "sub_xyz789",
            "status": "active",
            "cancel_at_period_end": True,
        }

    async def test_cancels_immediately(self, client: StripeClient) -> None:
        mock_sub = MagicMock()
        mock_sub.id = "sub_xyz789"
        mock_sub.status = "canceled"

        with patch("stripe.Subscription.cancel", return_value=mock_sub) as mock_cancel:
            result = await client.cancel_subscription(
                "sub_xyz789", at_period_end=False
            )

        mock_cancel.assert_called_once_with("sub_xyz789")
        assert result == {
            "id": "sub_xyz789",
            "status": "canceled",
        }


class TestConstructWebhookEvent:
    async def test_returns_event_dict(self, client: StripeClient) -> None:
        mock_event = {"type": "invoice.paid", "data": {"object": {}}}

        with patch(
            "stripe.Webhook.construct_event", return_value=mock_event
        ) as mock_construct:
            result = await client.construct_webhook_event(
                payload=b'{"type":"invoice.paid"}',
                sig_header="t=123,v1=abc",
                secret="whsec_test",
            )

        mock_construct.assert_called_once_with(
            b'{"type":"invoice.paid"}', "t=123,v1=abc", "whsec_test"
        )
        assert result == mock_event

    async def test_invalid_signature_raises_app_error_400(
        self, client: StripeClient
    ) -> None:
        with patch(
            "stripe.Webhook.construct_event",
            side_effect=stripe.SignatureVerificationError(
                "Invalid signature", "t=123,v1=abc"
            ),
        ):
            with pytest.raises(AppError) as exc_info:
                await client.construct_webhook_event(
                    payload=b"bad", sig_header="t=123,v1=abc", secret="whsec_test"
                )

        assert exc_info.value.status_code == 400
        assert "Invalid signature" in exc_info.value.message
