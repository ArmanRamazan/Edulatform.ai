"""Tests for LLM config routes: GET/PUT /ai/config/llm/{org_id} and POST test."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def admin_token(settings):
    payload = {
        "sub": str(uuid4()),
        "role": "admin",
        "subscription_tier": "enterprise",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def student_token(settings):
    payload = {
        "sub": str(uuid4()),
        "role": "student",
        "subscription_tier": "free",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@pytest.fixture
def org_id():
    return str(uuid4())


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def mock_resolver():
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def mock_http_client():
    return AsyncMock()


@pytest.fixture
def client(mock_cache, mock_resolver, mock_http_client):
    from app.routes.llm_config_routes import router, _get_llm_resolver, _get_cache

    from fastapi import FastAPI
    from common.errors import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    app.dependency_overrides[_get_llm_resolver] = lambda: mock_resolver
    app.dependency_overrides[_get_cache] = lambda: mock_cache

    return TestClient(app)


# --- GET /ai/config/llm/{org_id} ---


def test_get_config_returns_default_when_no_config(client, admin_token, org_id, mock_cache):
    mock_cache.get_llm_config.return_value = None

    resp = client.get(
        f"/ai/config/llm/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["internal_provider"] == "gemini"
    assert data["data_isolation"] == "standard"


def test_get_config_returns_stored_config(client, admin_token, org_id, mock_cache):
    stored = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
        "external_provider": "gemini",
        "embedding_provider": "gemini",
        "data_isolation": "strict",
    }
    mock_cache.get_llm_config.return_value = json.dumps(stored)

    resp = client.get(
        f"/ai/config/llm/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["internal_provider"] == "self_hosted"
    assert data["data_isolation"] == "strict"


def test_get_config_forbidden_for_student(client, student_token, org_id):
    resp = client.get(
        f"/ai/config/llm/{org_id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403


def test_get_config_requires_auth(client, org_id):
    resp = client.get(f"/ai/config/llm/{org_id}")

    assert resp.status_code in (401, 422)


# --- PUT /ai/config/llm/{org_id} ---


def test_put_config_updates_config(client, admin_token, org_id, mock_cache):
    body = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
        "data_isolation": "strict",
    }

    resp = client.put(
        f"/ai/config/llm/{org_id}",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    mock_cache.set_llm_config.assert_called_once()


def test_put_config_rejects_invalid_strict_without_self_hosted(client, admin_token, org_id):
    body = {
        "internal_provider": "gemini",
        "data_isolation": "strict",
    }

    resp = client.put(
        f"/ai/config/llm/{org_id}",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 400


def test_put_config_rejects_self_hosted_without_url(client, admin_token, org_id):
    body = {
        "internal_provider": "self_hosted",
        "data_isolation": "standard",
    }

    resp = client.put(
        f"/ai/config/llm/{org_id}",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 400


def test_put_config_forbidden_for_student(client, student_token, org_id):
    body = {"internal_provider": "gemini"}

    resp = client.put(
        f"/ai/config/llm/{org_id}",
        json=body,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403


# --- POST /ai/config/llm/{org_id}/test ---


def test_test_connection_success(client, admin_token, org_id, mock_resolver):
    mock_provider = AsyncMock()
    mock_provider.complete.return_value = ("pong", 5, 2)
    mock_resolver.resolve_from_config.return_value = mock_provider

    body = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
        "data_isolation": "standard",
    }

    resp = client.post(
        f"/ai/config/llm/{org_id}/test",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_test_connection_failure(client, admin_token, org_id, mock_resolver):
    mock_provider = AsyncMock()
    mock_provider.complete.side_effect = Exception("Connection refused")
    mock_resolver.resolve_from_config.return_value = mock_provider

    body = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
        "data_isolation": "standard",
    }

    resp = client.post(
        f"/ai/config/llm/{org_id}/test",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "error" in data


def test_test_connection_forbidden_for_student(client, student_token, org_id):
    body = {
        "internal_provider": "self_hosted",
        "internal_model_url": "http://vllm:8000/v1",
    }

    resp = client.post(
        f"/ai/config/llm/{org_id}/test",
        json=body,
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert resp.status_code == 403
