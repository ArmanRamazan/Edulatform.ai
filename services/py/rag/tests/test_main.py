from fastapi import FastAPI

from app.main import app


def test_app_is_fastapi_instance() -> None:
    assert isinstance(app, FastAPI)


def test_app_title() -> None:
    assert app.title == "RAG Service"


def test_health_routes_registered() -> None:
    routes = [r.path for r in app.routes]
    assert "/health/live" in routes
    assert "/health/ready" in routes
