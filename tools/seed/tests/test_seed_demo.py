"""Tests for seed_demo_org — Acme Engineering B2B demo organization."""
import uuid
from unittest.mock import AsyncMock

import bcrypt
import pytest

from seed import DEMO_ORG_ID, DEMO_USER_ID, _hash_password, seed_demo_org


# ---------------------------------------------------------------------------
# Unit test: password helper
# ---------------------------------------------------------------------------


def test_hash_password_produces_valid_bcrypt():
    hashed = _hash_password("demo123")
    assert bcrypt.checkpw(b"demo123", hashed.encode())


def test_hash_password_different_passwords_produce_different_hashes():
    hash1 = _hash_password("demo123")
    hash2 = _hash_password("sarah123")
    assert hash1 != hash2


def test_hash_password_rejects_wrong_password():
    hashed = _hash_password("demo123")
    assert not bcrypt.checkpw(b"wrong_password", hashed.encode())


# ---------------------------------------------------------------------------
# Idempotency: skips when demo user already exists
# ---------------------------------------------------------------------------


async def test_seed_demo_org_skips_when_already_seeded():
    identity_pool = AsyncMock()
    payment_pool = AsyncMock()

    # Simulate demo user already in DB
    identity_pool.fetchval.return_value = DEMO_USER_ID

    await seed_demo_org(identity_pool, payment_pool)

    identity_pool.execute.assert_not_called()
    payment_pool.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path: creates org, admin user, members, subscription
# ---------------------------------------------------------------------------


def _make_pools() -> tuple[AsyncMock, AsyncMock]:
    """Return (identity_pool, payment_pool) mocks configured for a fresh DB."""
    identity_pool = AsyncMock()
    payment_pool = AsyncMock()

    # Existence check → None (not yet seeded); then 9 INSERT...RETURNING UUIDs
    member_uuids = [str(uuid.uuid4()) for _ in range(9)]
    identity_pool.fetchval.side_effect = [None] + member_uuids

    return identity_pool, payment_pool


async def test_seed_demo_org_inserts_demo_admin_user():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    # At least one execute call must contain demo@acme.com
    found = any(
        "demo@acme.com" in str(c.args)
        for c in identity_pool.execute.call_args_list
    )
    assert found, "Expected INSERT with demo@acme.com"


async def test_seed_demo_org_demo_password_is_valid_bcrypt():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    # Find the execute call that inserts the demo admin user (contains demo@acme.com)
    demo_call = next(
        (c for c in identity_pool.execute.call_args_list if "demo@acme.com" in str(c.args)),
        None,
    )
    assert demo_call is not None, "No execute call for demo@acme.com"

    # args layout: (sql, DEMO_USER_ID, email, password_hash, name)
    password_hash: str = demo_call.args[3]
    assert bcrypt.checkpw(b"demo123", password_hash.encode()), "demo123 must verify against stored hash"


async def test_seed_demo_org_inserts_organization():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    found = any(
        "Acme Engineering" in str(c.args)
        for c in identity_pool.execute.call_args_list
    )
    assert found, "Expected INSERT with 'Acme Engineering'"


async def test_seed_demo_org_inserts_org_with_fixed_id():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    found = any(
        DEMO_ORG_ID in str(c.args)
        for c in identity_pool.execute.call_args_list
    )
    assert found, f"Expected INSERT with fixed DEMO_ORG_ID={DEMO_ORG_ID}"


async def test_seed_demo_org_adds_admin_to_org():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    # There must be an execute call that inserts 'admin' role into org_members
    found = any(
        "admin" in str(c.args) and DEMO_USER_ID in str(c.args)
        for c in identity_pool.execute.call_args_list
    )
    assert found, "Expected org_members INSERT with role=admin for demo user"


async def test_seed_demo_org_creates_nine_team_members():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    # fetchval called: 1 existence check + 9 member INSERT...RETURNING = 10
    assert identity_pool.fetchval.call_count == 10, (
        f"Expected 10 fetchval calls (1 check + 9 members), "
        f"got {identity_pool.fetchval.call_count}"
    )


async def test_seed_demo_org_creates_enterprise_subscription():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    assert payment_pool.execute.called, "Expected payment_pool.execute to be called"

    call_sql: str = payment_pool.execute.call_args[0][0]
    assert "enterprise" in call_sql, "Expected plan_tier='enterprise' in SQL"
    assert "100000" in call_sql, "Expected price_cents=100000 in SQL"


async def test_seed_demo_org_subscription_org_id_is_fixed():
    identity_pool, payment_pool = _make_pools()

    await seed_demo_org(identity_pool, payment_pool)

    # First positional arg after the SQL is the org_id
    call_args = payment_pool.execute.call_args[0]
    assert str(call_args[1]) == DEMO_ORG_ID, (
        f"Expected org subscription to use DEMO_ORG_ID={DEMO_ORG_ID}"
    )
