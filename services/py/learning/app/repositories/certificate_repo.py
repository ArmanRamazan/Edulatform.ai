from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError
from app.domain.certificate import Certificate

_COLUMNS = "id, user_id, course_id, issued_at, certificate_number, template_data"


class CertificateRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        user_id: UUID,
        course_id: UUID,
        certificate_number: str,
        template_data: dict | None = None,
    ) -> Certificate:
        import json

        try:
            row = await self._pool.fetchrow(
                f"""
                INSERT INTO certificates (user_id, course_id, certificate_number, template_data)
                VALUES ($1, $2, $3, $4)
                RETURNING {_COLUMNS}
                """,
                user_id,
                course_id,
                certificate_number,
                json.dumps(template_data or {}),
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Certificate already issued for this course") from exc
        return self._to_certificate(row)

    async def get_by_id(self, certificate_id: UUID) -> Certificate | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM certificates WHERE id = $1",
            certificate_id,
        )
        return self._to_certificate(row) if row else None

    async def get_by_user(self, user_id: UUID) -> list[Certificate]:
        rows = await self._pool.fetch(
            f"SELECT {_COLUMNS} FROM certificates WHERE user_id = $1 ORDER BY issued_at DESC",
            user_id,
        )
        return [self._to_certificate(row) for row in rows]

    async def get_by_user_and_course(
        self, user_id: UUID, course_id: UUID,
    ) -> Certificate | None:
        row = await self._pool.fetchrow(
            f"SELECT {_COLUMNS} FROM certificates WHERE user_id = $1 AND course_id = $2",
            user_id,
            course_id,
        )
        return self._to_certificate(row) if row else None

    @staticmethod
    def _to_certificate(row: asyncpg.Record) -> Certificate:
        import json

        template_data = row["template_data"]
        if isinstance(template_data, str):
            template_data = json.loads(template_data)
        elif template_data is None:
            template_data = {}

        return Certificate(
            id=row["id"],
            user_id=row["user_id"],
            course_id=row["course_id"],
            issued_at=row["issued_at"],
            certificate_number=row["certificate_number"],
            template_data=template_data,
        )
