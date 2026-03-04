from __future__ import annotations

from uuid import UUID

import asyncpg

from app.domain.lesson import Lesson

_ALLOWED_UPDATE_COLUMNS = frozenset({
    "title", "content", "video_url", "duration_minutes", "order",
})


class LessonRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        module_id: UUID,
        title: str,
        content: str,
        video_url: str | None,
        duration_minutes: int,
        order: int,
    ) -> Lesson:
        row = await self._pool.fetchrow(
            """
            INSERT INTO lessons (module_id, title, content, video_url, duration_minutes, "order")
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, module_id, title, content, video_url, duration_minutes, "order", created_at
            """,
            module_id,
            title,
            content,
            video_url,
            duration_minutes,
            order,
        )
        return self._to_entity(row)

    async def get_by_id(self, lesson_id: UUID) -> Lesson | None:
        row = await self._pool.fetchrow(
            'SELECT id, module_id, title, content, video_url, duration_minutes, "order", created_at '
            "FROM lessons WHERE id = $1",
            lesson_id,
        )
        return self._to_entity(row) if row else None

    async def list_by_module(self, module_id: UUID) -> list[Lesson]:
        rows = await self._pool.fetch(
            'SELECT id, module_id, title, content, video_url, duration_minutes, "order", created_at '
            'FROM lessons WHERE module_id = $1 ORDER BY "order"',
            module_id,
        )
        return [self._to_entity(r) for r in rows]

    async def update(self, lesson_id: UUID, **fields: object) -> Lesson | None:
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
            return await self.get_by_id(lesson_id)
        values.append(lesson_id)
        row = await self._pool.fetchrow(
            f'UPDATE lessons SET {", ".join(sets)} WHERE id = ${idx} '
            f'RETURNING id, module_id, title, content, video_url, duration_minutes, "order", created_at',
            *values,
        )
        return self._to_entity(row) if row else None

    async def delete(self, lesson_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM lessons WHERE id = $1", lesson_id
        )
        return result == "DELETE 1"

    async def count_by_course(self, course_id: UUID) -> int:
        count = await self._pool.fetchval(
            """
            SELECT count(*) FROM lessons l
            JOIN modules m ON l.module_id = m.id
            WHERE m.course_id = $1
            """,
            course_id,
        )
        return count

    @staticmethod
    def _to_entity(row: asyncpg.Record) -> Lesson:
        return Lesson(
            id=row["id"],
            module_id=row["module_id"],
            title=row["title"],
            content=row["content"],
            video_url=row["video_url"],
            duration_minutes=row["duration_minutes"],
            order=row["order"],
            created_at=row["created_at"],
        )
