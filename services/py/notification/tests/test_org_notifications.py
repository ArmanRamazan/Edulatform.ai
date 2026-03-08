"""Tests for organization_id support in notifications (B2B multi-tenancy)."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from common.errors import register_error_handlers
from common.security import create_access_token
from app.domain.notification import Notification, NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.routes.notifications import router
from app.services.notification_service import NotificationService


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def mock_repo_for_org():
    return AsyncMock(spec=NotificationRepository)


@pytest.fixture
def svc(mock_repo_for_org):
    return NotificationService(repo=mock_repo_for_org)


def _make_notification(user_id, org_id=None):
    return Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="B2B notification",
        body="Welcome to the org!",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        organization_id=org_id,
    )


@pytest.mark.asyncio
async def test_create_notification_stores_org_id(svc, mock_repo_for_org, org_id):
    """Service passes organization_id to repo when creating a notification."""
    user_id = uuid4()
    expected = _make_notification(user_id, org_id)
    mock_repo_for_org.create.return_value = expected

    result = await svc.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="B2B notification",
        body="Welcome to the org!",
        organization_id=org_id,
    )

    assert result.organization_id == org_id
    mock_repo_for_org.create.assert_called_once_with(
        user_id,
        NotificationType.ENROLLMENT,
        "B2B notification",
        "Welcome to the org!",
        False,
        org_id,
    )


@pytest.mark.asyncio
async def test_create_notification_without_org_id_backward_compat(svc, mock_repo_for_org):
    """Notifications without org_id still work (B2C backward compatibility)."""
    user_id = uuid4()
    expected = _make_notification(user_id, org_id=None)
    mock_repo_for_org.create.return_value = expected

    result = await svc.create(
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="B2B notification",
        body="Welcome to the org!",
    )

    assert result.organization_id is None
    mock_repo_for_org.create.assert_called_once_with(
        user_id,
        NotificationType.ENROLLMENT,
        "B2B notification",
        "Welcome to the org!",
        False,
        None,
    )


@pytest.mark.asyncio
async def test_list_by_org(svc, mock_repo_for_org, org_id):
    """Service delegates list_by_org to the repo filtered by organization_id."""
    user_id = uuid4()
    notifications = [_make_notification(user_id, org_id)]
    mock_repo_for_org.list_by_org.return_value = (notifications, 1)

    items, total = await svc.list_by_org(org_id, limit=20, offset=0)

    assert total == 1
    assert items[0].organization_id == org_id
    mock_repo_for_org.list_by_org.assert_called_once_with(org_id, 20, 0)


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_svc_for_routes():
    return AsyncMock(spec=NotificationService)


@pytest.fixture
def test_app_org(mock_svc_for_routes):
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    import app.main as main_module
    main_module.app_settings = type("S", (), {
        "jwt_secret": "test-secret",
        "jwt_algorithm": "HS256",
    })()
    main_module._notification_service = mock_svc_for_routes

    return app


@pytest.fixture
async def org_client(test_app_org):
    transport = ASGITransport(app=test_app_org)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def route_org_id():
    return uuid4()


@pytest.fixture
def org_member_token(route_org_id):
    user_id = uuid4()
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={
            "role": "student",
            "is_verified": True,
            "organization_id": str(route_org_id),
        },
    )


@pytest.fixture
def token_without_org():
    user_id = uuid4()
    return create_access_token(
        str(user_id), "test-secret",
        extra_claims={"role": "student", "is_verified": False},
    )


@pytest.mark.asyncio
async def test_create_notification_jwt_org_id_forwarded(
    org_client, mock_svc_for_routes, route_org_id, org_member_token,
):
    """Route extracts organization_id from JWT and passes it to the service."""
    user_id = uuid4()
    mock_svc_for_routes.create.return_value = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Welcome",
        body="",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        organization_id=route_org_id,
    )

    resp = await org_client.post(
        "/notifications",
        json={"type": "enrollment", "title": "Welcome", "body": ""},
        headers={"Authorization": f"Bearer {org_member_token}"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["organization_id"] == str(route_org_id)

    call_kwargs = mock_svc_for_routes.create.call_args.kwargs
    assert call_kwargs["organization_id"] == route_org_id


@pytest.mark.asyncio
async def test_create_notification_no_org_in_jwt(
    org_client, mock_svc_for_routes, token_without_org,
):
    """Route passes organization_id=None when JWT has no organization_id."""
    user_id = uuid4()
    mock_svc_for_routes.create.return_value = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Legacy",
        body="",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        organization_id=None,
    )

    resp = await org_client.post(
        "/notifications",
        json={"type": "enrollment", "title": "Legacy", "body": ""},
        headers={"Authorization": f"Bearer {token_without_org}"},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["organization_id"] is None

    call_kwargs = mock_svc_for_routes.create.call_args.kwargs
    assert call_kwargs.get("organization_id") is None


@pytest.mark.asyncio
async def test_list_org_notifications_endpoint(
    org_client, mock_svc_for_routes, route_org_id, org_member_token,
):
    """GET /notifications/org returns notifications scoped to the JWT organization."""
    user_id = uuid4()
    notif = Notification(
        id=uuid4(),
        user_id=user_id,
        type=NotificationType.ENROLLMENT,
        title="Org notif",
        body="",
        is_read=False,
        created_at=datetime.now(timezone.utc),
        organization_id=route_org_id,
    )
    mock_svc_for_routes.list_by_org.return_value = ([notif], 1)

    resp = await org_client.get(
        "/notifications/org",
        headers={"Authorization": f"Bearer {org_member_token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["organization_id"] == str(route_org_id)
    mock_svc_for_routes.list_by_org.assert_called_once_with(route_org_id, 20, 0)


@pytest.mark.asyncio
async def test_list_org_notifications_no_org_in_jwt(
    org_client, mock_svc_for_routes, token_without_org,
):
    """GET /notifications/org returns 403 when JWT has no organization_id."""
    resp = await org_client.get(
        "/notifications/org",
        headers={"Authorization": f"Bearer {token_without_org}"},
    )

    assert resp.status_code == 403
