from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.module import Module

_ALLOWED_UPDATE_COLUMNS = frozenset({
    "title", "order",
})


class ModuleRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, course_id: UUID, title: str, order: int) -> Module:
        row = await self._pool.fetchrow(
            """
            INSERT INTO modules (course_id, title, "order")
            VALUES ($1, $2, $3)
            RETURNING id, course_id, title, "order", created_at
            """,
            course_id,
            title,
            order,
        )
        return self._to_entity(row)

    async def get_by_id(self, module_id: UUID) -> Module | None:
        row = await self._pool.fetchrow(
            'SELECT id, course_id, title, "order", created_at FROM modules WHERE id = $1',
            module_id,
        )
        return self._to_entity(row) if row else None

    async def list_by_course(self, course_id: UUID) -> list[Module]:
        rows = await self._pool.fetch(
            'SELECT id, course_id, title, "order", created_at FROM modules WHERE course_id = $1 ORDER BY "order"',
            course_id,
        )
        return [self._to_entity(r) for r in rows]

    async def update(self, module_id: UUID, **fields: object) -> Module | None:
        sets: list[str] = []
        values: list[object] = []
        idx = 1
        for key, val in fields.items():
            if key not in _ALLOWED_UPDATE_COLUMNS:
                raise ValueError(f"Cannot update column: {key}")
            col = f'"{key}"' if key == "order" else key
            sets.append(f"{col} = ${idx}")
            values.append(val)
            idx += 1
        if not sets:
            return await self.get_by_id(module_id)
        values.append(module_id)
        row = await self._pool.fetchrow(
            f'UPDATE modules SET {", ".join(sets)} WHERE id = ${idx} '
            f'RETURNING id, course_id, title, "order", created_at',
            *values,
        )
        return self._to_entity(row) if row else None

    async def delete(self, module_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM modules WHERE id = $1", module_id
        )
        return result == "DELETE 1"

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Module:
        return Module(
            id=row["id"],
            course_id=row["course_id"],
            title=row["title"],
            order=row["order"],
            created_at=row["created_at"],
        )
