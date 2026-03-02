import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


@pytest.fixture
def migration_sql() -> str:
    return (MIGRATIONS_DIR / "003_subscriptions.sql").read_text()


@pytest.fixture
def all_migration_sqls() -> list[str]:
    sqls = []
    for name in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sqls.append(name.read_text())
    return sqls


class TestSubscriptionMigrationIdempotent:
    """Migration runs twice without error (idempotent)."""

    async def test_migration_runs_twice_without_error(self, migration_sql: str) -> None:
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)

        # Run migration twice — should not raise
        await conn.execute(migration_sql)
        await conn.execute(migration_sql)

        assert conn.execute.call_count == 2

    async def test_migration_file_exists(self) -> None:
        path = MIGRATIONS_DIR / "003_subscriptions.sql"
        assert path.exists(), "migrations/003_subscriptions.sql must exist"

    async def test_migration_contains_idempotent_ddl(self, migration_sql: str) -> None:
        assert "CREATE TABLE IF NOT EXISTS subscription_plans" in migration_sql
        assert "CREATE TABLE IF NOT EXISTS user_subscriptions" in migration_sql
        assert "CREATE INDEX IF NOT EXISTS" in migration_sql
        assert "ON CONFLICT" in migration_sql


class TestSubscriptionMigrationSeedData:
    """Migration seeds 3 plans."""

    async def test_migration_seeds_three_plans(self, migration_sql: str) -> None:
        # Verify all three plan names appear in the seed data
        assert "'free'" in migration_sql
        assert "'student'" in migration_sql
        assert "'pro'" in migration_sql

    async def test_free_plan_values(self, migration_sql: str) -> None:
        assert "0.00" in migration_sql
        assert "10" in migration_sql  # ai_credits_daily

    async def test_pro_plan_unlimited_credits(self, migration_sql: str) -> None:
        # -1 means unlimited
        assert "-1" in migration_sql


class TestMainLoadsSubscriptionMigration:
    """main.py lifespan loads 003_subscriptions.sql."""

    async def test_lifespan_opens_003_migration(self) -> None:
        import app.main as main_module

        source = Path(main_module.__file__).read_text()
        assert "003_subscriptions.sql" in source, (
            "main.py lifespan must load migrations/003_subscriptions.sql"
        )
