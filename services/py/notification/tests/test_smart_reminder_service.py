import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx

from app.domain.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.services.smart_reminder_service import SmartReminderService


@pytest.fixture
def mock_repo():
    return AsyncMock(spec=NotificationRepository)


@pytest.fixture
def mock_http_client():
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def service(mock_repo, mock_http_client):
    return SmartReminderService(
        repo=mock_repo,
        http_client=mock_http_client,
        learning_service_url="http://learning:8007/api/learning",
        jwt_secret="test-secret",
    )


def _make_due_response(total: int) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"items": [], "total": total}
    return resp


def _make_streak_response(
    current_streak: int = 0,
    last_activity_date: str | None = None,
    active_today: bool = False,
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {
        "current_streak": current_streak,
        "longest_streak": current_streak,
        "last_activity_date": last_activity_date or str(date.today()),
        "active_today": active_today,
    }
    return resp


@pytest.mark.asyncio
async def test_sends_reminder_when_due_cards_above_threshold(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """User with >5 due cards and no recent review → reminder sent."""
    user1 = uuid4()
    mock_repo.get_distinct_user_ids.return_value = [user1]
    mock_repo.has_unread_by_type.return_value = False

    mock_http_client.get.side_effect = [
        _make_due_response(total=10),
        _make_streak_response(current_streak=1, active_today=False),
    ]

    result = await service.send_smart_reminders()

    assert result["reminders_sent"] == 1
    assert result["users_checked"] == 1
    mock_repo.create.assert_called_once_with(
        user1,
        NotificationType.FLASHCARD_REMINDER,
        "Время для повторения!",
        "У вас 10 карточек для повторения. Не дайте знаниям забыться!",
    )


@pytest.mark.asyncio
async def test_skips_user_with_active_streak(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """User with active streak > 3 days → no reminder."""
    user1 = uuid4()
    mock_repo.get_distinct_user_ids.return_value = [user1]
    mock_repo.has_unread_by_type.return_value = False

    mock_http_client.get.side_effect = [
        _make_due_response(total=10),
        _make_streak_response(current_streak=5, active_today=True),
    ]

    result = await service.send_smart_reminders()

    assert result["reminders_sent"] == 0
    assert result["skipped_active_streak"] == 1
    mock_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_skips_user_with_low_due_cards(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """User with <=5 due cards → no reminder."""
    user1 = uuid4()
    mock_repo.get_distinct_user_ids.return_value = [user1]
    mock_repo.has_unread_by_type.return_value = False

    mock_http_client.get.side_effect = [
        _make_due_response(total=3),
    ]

    result = await service.send_smart_reminders()

    assert result["reminders_sent"] == 0
    assert result["skipped_low_cards"] == 1
    mock_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_skips_user_when_learning_service_unavailable(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """Learning service unavailable → skip user, continue with others."""
    user1, user2 = uuid4(), uuid4()
    mock_repo.get_distinct_user_ids.return_value = [user1, user2]
    mock_repo.has_unread_by_type.return_value = False

    mock_http_client.get.side_effect = [
        httpx.ConnectError("Connection refused"),
        _make_due_response(total=10),
        _make_streak_response(current_streak=0, active_today=False),
    ]

    result = await service.send_smart_reminders()

    assert result["users_checked"] == 2
    assert result["reminders_sent"] == 1
    assert result["skipped_errors"] == 1


@pytest.mark.asyncio
async def test_deduplication_skips_existing_unread(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """Don't send if user already has unread flashcard reminder."""
    user1 = uuid4()
    mock_repo.get_distinct_user_ids.return_value = [user1]
    mock_repo.has_unread_by_type.return_value = True

    result = await service.send_smart_reminders()

    assert result["reminders_sent"] == 0
    assert result["skipped_existing"] == 1
    mock_http_client.get.assert_not_called()
    mock_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_handles_multiple_users_mixed(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """Multiple users with different conditions."""
    user_send = uuid4()      # >5 due, low streak → send
    user_streak = uuid4()    # >5 due, high streak → skip
    user_low = uuid4()       # <=5 due → skip

    mock_repo.get_distinct_user_ids.return_value = [user_send, user_streak, user_low]
    mock_repo.has_unread_by_type.return_value = False

    mock_http_client.get.side_effect = [
        # user_send
        _make_due_response(total=8),
        _make_streak_response(current_streak=2, active_today=False),
        # user_streak
        _make_due_response(total=15),
        _make_streak_response(current_streak=7, active_today=True),
        # user_low
        _make_due_response(total=2),
    ]

    result = await service.send_smart_reminders()

    assert result["users_checked"] == 3
    assert result["reminders_sent"] == 1
    assert result["skipped_active_streak"] == 1
    assert result["skipped_low_cards"] == 1


@pytest.mark.asyncio
async def test_empty_user_list(
    service: SmartReminderService,
    mock_repo: AsyncMock,
    mock_http_client: AsyncMock,
):
    """No users → no work."""
    mock_repo.get_distinct_user_ids.return_value = []

    result = await service.send_smart_reminders()

    assert result["users_checked"] == 0
    assert result["reminders_sent"] == 0
    mock_http_client.get.assert_not_called()
