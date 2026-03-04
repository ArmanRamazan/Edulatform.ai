import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()
