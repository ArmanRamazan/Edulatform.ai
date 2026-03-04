"""Tests for email-triggered notifications on lifecycle events."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.domain.notification import Notification, NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.services.notification_service import NotificationService
from app.adapters.email import EmailAdapter


EMAIL_TRIGGERING_TYPES = {"welcome", "course_completed", "review_received", "streak_at_risk"}

EXPECTED_SUBJECTS = {
    "welcome": "Добро пожаловать в EduPlatform!",
    "course_completed": "Поздравляем с завершением курса!",
    "review_received": "Новый отзыв на ваш курс",
    "streak_at_risk": "Ваша серия под угрозой!",
}


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=NotificationRepository)


@pytest.fixture
def mock_email_adapter():
    adapter = AsyncMock(spec=EmailAdapter)
    adapter.send.return_value = True
    return adapter


@pytest.fixture
def service_with_email(mock_repo, mock_email_adapter):
    return NotificationService(repo=mock_repo, email_adapter=mock_email_adapter)


@pytest.fixture
def service_without_email(mock_repo):
    return NotificationService(repo=mock_repo)


def _make_notification(
    user_id,
    ntype: NotificationType = NotificationType.ENROLLMENT,
    email_sent: bool = False,
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


class TestEmailTriggerForWelcome:
    @pytest.mark.asyncio
    async def test_welcome_with_email_sends_email(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=True)
        mock_repo.create.return_value = notif

        result = await service_with_email.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome!",
            body="Welcome to EduPlatform",
            email="user@example.com",
        )

        mock_email_adapter.send.assert_called_once_with(
            to_email="user@example.com",
            subject="Добро пожаловать в EduPlatform!",
            body="Welcome to EduPlatform",
        )
        assert result.email_sent is True


class TestEmailTriggerForCourseCompleted:
    @pytest.mark.asyncio
    async def test_course_completed_sends_email(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.COURSE_COMPLETED, email_sent=True)
        mock_repo.create.return_value = notif

        result = await service_with_email.create(
            user_id=user_id,
            type=NotificationType.COURSE_COMPLETED,
            title="Course done!",
            body="You finished the course",
            email="user@example.com",
        )

        mock_email_adapter.send.assert_called_once_with(
            to_email="user@example.com",
            subject="Поздравляем с завершением курса!",
            body="You finished the course",
        )


class TestEmailTriggerForReviewReceived:
    @pytest.mark.asyncio
    async def test_review_received_sends_email(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.REVIEW_RECEIVED, email_sent=True)
        mock_repo.create.return_value = notif

        await service_with_email.create(
            user_id=user_id,
            type=NotificationType.REVIEW_RECEIVED,
            title="New review",
            body="Someone reviewed your course",
            email="teacher@example.com",
        )

        mock_email_adapter.send.assert_called_once_with(
            to_email="teacher@example.com",
            subject="Новый отзыв на ваш курс",
            body="Someone reviewed your course",
        )


class TestEmailTriggerForStreakAtRisk:
    @pytest.mark.asyncio
    async def test_streak_at_risk_sends_email(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.STREAK_AT_RISK, email_sent=True)
        mock_repo.create.return_value = notif

        await service_with_email.create(
            user_id=user_id,
            type=NotificationType.STREAK_AT_RISK,
            title="Streak warning",
            body="Your streak is at risk!",
            email="user@example.com",
        )

        mock_email_adapter.send.assert_called_once_with(
            to_email="user@example.com",
            subject="Ваша серия под угрозой!",
            body="Your streak is at risk!",
        )


class TestNoEmailForRegularTypes:
    @pytest.mark.asyncio
    async def test_enrollment_type_does_not_trigger_email(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.ENROLLMENT, email_sent=False)
        mock_repo.create.return_value = notif

        await service_with_email.create(
            user_id=user_id,
            type=NotificationType.ENROLLMENT,
            title="Enrolled",
            body="You enrolled",
            email="user@example.com",
        )

        mock_email_adapter.send.assert_not_called()


class TestNoEmailWhenNoEmailProvided:
    @pytest.mark.asyncio
    async def test_welcome_without_email_skips_sending(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=False)
        mock_repo.create.return_value = notif

        await service_with_email.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome!",
            body="Hello",
        )

        mock_email_adapter.send.assert_not_called()


class TestEmailSentFlag:
    @pytest.mark.asyncio
    async def test_email_sent_true_when_email_succeeds(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=True)
        mock_repo.create.return_value = notif
        mock_email_adapter.send.return_value = True

        result = await service_with_email.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome",
            body="Hi",
            email="user@example.com",
        )

        mock_repo.create.assert_called_once_with(
            user_id, NotificationType.WELCOME, "Welcome", "Hi", True,
        )

    @pytest.mark.asyncio
    async def test_email_sent_false_when_email_fails(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=False)
        mock_repo.create.return_value = notif
        mock_email_adapter.send.return_value = False

        result = await service_with_email.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome",
            body="Hi",
            email="user@example.com",
        )

        mock_repo.create.assert_called_once_with(
            user_id, NotificationType.WELCOME, "Welcome", "Hi", False,
        )


class TestEmailFailureHandling:
    @pytest.mark.asyncio
    async def test_email_exception_does_not_fail_notification(
        self, service_with_email, mock_repo, mock_email_adapter, user_id,
    ):
        """Email sending exception should NOT prevent notification creation."""
        notif = _make_notification(user_id, NotificationType.WELCOME, email_sent=False)
        mock_repo.create.return_value = notif
        mock_email_adapter.send.side_effect = Exception("SMTP connection failed")

        result = await service_with_email.create(
            user_id=user_id,
            type=NotificationType.WELCOME,
            title="Welcome",
            body="Hi",
            email="user@example.com",
        )

        # Notification still created with email_sent=False
        assert result is not None
        mock_repo.create.assert_called_once_with(
            user_id, NotificationType.WELCOME, "Welcome", "Hi", False,
        )


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_create_without_email_arg_works(
        self, service_without_email, mock_repo, user_id,
    ):
        """Service without email adapter still works (backward compatible)."""
        notif = _make_notification(user_id, email_sent=False)
        mock_repo.create.return_value = notif

        result = await service_without_email.create(
            user_id=user_id,
            type=NotificationType.ENROLLMENT,
            title="Enrolled",
            body="Welcome",
        )

        assert result is not None
        mock_repo.create.assert_called_once_with(
            user_id, NotificationType.ENROLLMENT, "Enrolled", "Welcome", False,
        )

    @pytest.mark.asyncio
    async def test_service_init_without_email_adapter(self, mock_repo):
        """Service can be initialized without email adapter."""
        service = NotificationService(repo=mock_repo)
        assert service._email_adapter is None
