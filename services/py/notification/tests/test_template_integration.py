"""Tests for email template integration with notification service."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.notification import Notification, NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.services.notification_service import NotificationService
from app.adapters.email import EmailClient


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=NotificationRepository)


@pytest.fixture
def mock_email_adapter():
    adapter = AsyncMock(spec=EmailClient)
    adapter.send.return_value = True
    return adapter


@pytest.fixture
def service(mock_repo, mock_email_adapter):
    return NotificationService(repo=mock_repo, email_adapter=mock_email_adapter)


def _make_notification(
    user_id, ntype: NotificationType, email_sent: bool = False,
) -> Notification:
    return Notification(
        id=uuid4(),
        user_id=user_id,
        type=ntype,
        title="Test",
        body="Test body",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        email_sent=email_sent,
    )


class TestTemplateIntegration:
    @pytest.mark.asyncio
    async def test_welcome_with_template_kwargs_uses_template(
        self, service, mock_repo, mock_email_adapter, user_id,
    ):
        """When template_kwargs provided, email uses HTML template."""
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=True)
        mock_repo.create.return_value = notif

        await service.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome!",
            body="Welcome to EduPlatform",
            email="user@example.com",
            template_kwargs={"user_name": "Иван"},
        )

        call_kwargs = mock_email_adapter.send.call_args
        assert call_kwargs.kwargs["subject"] == "Добро пожаловать в EduPlatform!"
        assert "<!DOCTYPE html>" in call_kwargs.kwargs["html_body"]
        assert "Иван" in call_kwargs.kwargs["html_body"]
        assert "Начать обучение" in call_kwargs.kwargs["html_body"]

    @pytest.mark.asyncio
    async def test_without_template_kwargs_uses_raw_body(
        self, service, mock_repo, mock_email_adapter, user_id,
    ):
        """Without template_kwargs, falls back to raw body (backward compat)."""
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=True)
        mock_repo.create.return_value = notif

        await service.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome!",
            body="Plain body text",
            email="user@example.com",
        )

        mock_email_adapter.send.assert_called_once_with(
            to="user@example.com",
            subject="Добро пожаловать в EduPlatform!",
            html_body="Plain body text",
        )

    @pytest.mark.asyncio
    async def test_template_kwargs_for_unknown_type_falls_back(
        self, service, mock_repo, mock_email_adapter, user_id,
    ):
        """If template_kwargs provided but no template for type, use raw body."""
        notif = _make_notification(user_id, NotificationType.STREAK_AT_RISK, email_sent=True)
        mock_repo.create.return_value = notif

        await service.create(
            user_id=user_id,
            type=NotificationType.STREAK_AT_RISK,
            title="Streak!",
            body="Your streak is at risk",
            email="user@example.com",
            template_kwargs={"user_name": "Иван"},
        )

        mock_email_adapter.send.assert_called_once_with(
            to="user@example.com",
            subject="Ваша серия под угрозой!",
            html_body="Your streak is at risk",
        )

    @pytest.mark.asyncio
    async def test_review_template_integration(
        self, service, mock_repo, mock_email_adapter, user_id,
    ):
        """Review template renders rating stars and review text."""
        notif = _make_notification(user_id, NotificationType.REVIEW_RECEIVED, email_sent=True)
        mock_repo.create.return_value = notif

        await service.create(
            user_id=user_id,
            type=NotificationType.REVIEW_RECEIVED,
            title="New review",
            body="Someone reviewed your course",
            email="teacher@example.com",
            template_kwargs={
                "teacher_name": "Алексей",
                "course_title": "Python 101",
                "rating": 5,
                "review_text": "Отличный курс!",
            },
        )

        call_kwargs = mock_email_adapter.send.call_args
        assert "Python 101" in call_kwargs.kwargs["subject"]
        assert "★★★★★" in call_kwargs.kwargs["html_body"]
        assert "Отличный курс!" in call_kwargs.kwargs["html_body"]
