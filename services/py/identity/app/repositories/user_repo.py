from uuid import UUID

import asyncpg

from app.domain.referral import generate_referral_code
from app.domain.user import PublicProfile, User, UserRole

_COLUMNS = "id, email, password_hash, name, role, is_verified, created_at, email_verified, referral_code"


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, email: str, password_hash: str, name: str, role: UserRole) -> User:
        referral_code = generate_referral_code()
        row = await self._pool.fetchrow(
            f"""
            INSERT INTO users (email, password_hash, name, role, referral_code)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING {_COLUMNS}
            """,
            email,
            password_hash,
            name,
            role,
            referral_code,
        )
        return self._to_entity(row)

    async def get_by_email(self, email: str) -> User | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM users WHERE email = $1",
            email,
        )
        return self._to_entity(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM users WHERE id = $1",
            user_id,
        )
        return self._to_entity(row) if row else None

    async def list_unverified_teachers(self, limit: int = 50, offset: int = 0) -> tuple[list[User], int]:
        total = await self._pool.fetchval(
            "SELECT count(*) FROM users WHERE role = 'teacher' AND is_verified = false",
        )
        rows = await self._pool.fetch(
            f"""
            SELECT {_COLUMNS}
            FROM users WHERE role = 'teacher' AND is_verified = false
            ORDER BY created_at
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
        return [self._to_entity(r) for r in rows], total

    async def set_verified(self, user_id: UUID, verified: bool) -> User | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE users SET is_verified = $2
            WHERE id = $1
            RETURNING {_COLUMNS}
            """,
            user_id,
            verified,
        )
        return self._to_entity(row) if row else None

    async def set_email_verified(self, user_id: UUID) -> User | None:
        row = await self._pool.fetchrow(
            f"""
            UPDATE users SET email_verified = true
            WHERE id = $1
            RETURNING {_COLUMNS}
            """,
            user_id,
        )
        return self._to_entity(row) if row else None

    async def update_password(self, user_id: UUID, password_hash: str) -> None:
        await self._pool.execute(
            "UPDATE users SET password_hash = $2 WHERE id = $1",
            user_id,
            password_hash,
        )

    async def get_referral_code(self, user_id: UUID) -> str | None:
        return await self._pool.fetchval(
            "SELECT referral_code FROM users WHERE id = $1",
            user_id,
        )

    async def set_referral_code(self, user_id: UUID, referral_code: str) -> str:
        await self._pool.execute(
            "UPDATE users SET referral_code = $2 WHERE id = $1",
            user_id,
            referral_code,
        )
        return referral_code

    async def get_public_profile(self, user_id: UUID) -> PublicProfile | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, name, bio, avatar_url, role, is_verified, created_at, is_public
            FROM users
            WHERE id = $1 AND is_public = true
            """,
            user_id,
        )
        if not row:
            return None
        return PublicProfile(
            id=row["id"],
            name=row["name"],
            bio=row["bio"],
            avatar_url=row["avatar_url"],
            role=UserRole(row["role"]),
            is_verified=row["is_verified"],
            created_at=row["created_at"],
            is_public=row["is_public"],
        )

    async def update_profile_visibility(self, user_id: UUID, is_public: bool) -> None:
        await self._pool.execute(
            "UPDATE users SET is_public = $2 WHERE id = $1",
            user_id,
            is_public,
        )

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> User:
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            name=row["name"],
            role=UserRole(row["role"]),
            is_verified=row["is_verified"],
            created_at=row["created_at"],
            email_verified=row["email_verified"],
            referral_code=row["referral_code"],
        )
