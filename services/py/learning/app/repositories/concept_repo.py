from __future__ import annotations

from uuid import UUID

import asyncpg

from common.errors import ConflictError, ForbiddenError
from app.domain.concept import Concept, ConceptPrerequisite, ConceptMastery

_CONCEPT_COLUMNS = 'id, course_id, lesson_id, name, description, parent_id, "order", created_at'


class ConceptRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        course_id: UUID,
        name: str,
        description: str = "",
        lesson_id: UUID | None = None,
        parent_id: UUID | None = None,
        order: int = 0,
    ) -> Concept:
        try:
            row = await self._pool.fetchrow(
                f"""
                INSERT INTO concepts (course_id, lesson_id, name, description, parent_id, "order")
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING {_CONCEPT_COLUMNS}
                """,
                course_id, lesson_id, name, description, parent_id, order,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError(f"Concept '{name}' already exists in this course") from exc
        return self._to_concept(row)

    async def get_by_id(self, concept_id: UUID) -> Concept | None:
        row = await self._pool.fetchrow(
            f"SELECT {_CONCEPT_COLUMNS} FROM concepts WHERE id = $1",
            concept_id,
        )
        return self._to_concept(row) if row else None

    async def get_by_course(self, course_id: UUID) -> list[Concept]:
        rows = await self._pool.fetch(
            f'SELECT {_CONCEPT_COLUMNS} FROM concepts WHERE course_id = $1 ORDER BY "order", created_at',
            course_id,
        )
        return [self._to_concept(r) for r in rows]

    async def get_by_lesson(self, lesson_id: UUID) -> list[Concept]:
        rows = await self._pool.fetch(
            f'SELECT {_CONCEPT_COLUMNS} FROM concepts WHERE lesson_id = $1 ORDER BY "order"',
            lesson_id,
        )
        return [self._to_concept(r) for r in rows]

    async def update(
        self,
        concept_id: UUID,
        name: str | None = None,
        description: str | None = None,
        lesson_id: UUID | None = ...,
        parent_id: UUID | None = ...,
        order: int | None = None,
    ) -> Concept | None:
        current = await self.get_by_id(concept_id)
        if current is None:
            return None

        new_name = name if name is not None else current.name
        new_desc = description if description is not None else current.description
        new_lesson = lesson_id if lesson_id is not ... else current.lesson_id
        new_parent = parent_id if parent_id is not ... else current.parent_id
        new_order = order if order is not None else current.order

        try:
            row = await self._pool.fetchrow(
                f"""
                UPDATE concepts
                SET name = $2, description = $3, lesson_id = $4, parent_id = $5, "order" = $6
                WHERE id = $1
                RETURNING {_CONCEPT_COLUMNS}
                """,
                concept_id, new_name, new_desc, new_lesson, new_parent, new_order,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError("Concept with this name already exists in the course") from exc
        return self._to_concept(row) if row else None

    async def delete(self, concept_id: UUID) -> bool:
        result = await self._pool.execute(
            "DELETE FROM concepts WHERE id = $1", concept_id
        )
        return result == "DELETE 1"

    # --- Prerequisites ---

    async def add_prerequisite(
        self, concept_id: UUID, prerequisite_id: UUID
    ) -> ConceptPrerequisite:
        try:
            row = await self._pool.fetchrow(
                """
                INSERT INTO concept_prerequisites (concept_id, prerequisite_id)
                VALUES ($1, $2)
                RETURNING id, concept_id, prerequisite_id
                """,
                concept_id, prerequisite_id,
            )
        except asyncpg.UniqueViolationError:
            raise ConflictError("Prerequisite already exists")
        except asyncpg.CheckViolationError as exc:
            raise ForbiddenError("A concept cannot be its own prerequisite") from exc
        return ConceptPrerequisite(
            id=row["id"],
            concept_id=row["concept_id"],
            prerequisite_id=row["prerequisite_id"],
        )

    async def remove_prerequisite(
        self, concept_id: UUID, prerequisite_id: UUID
    ) -> bool:
        result = await self._pool.execute(
            "DELETE FROM concept_prerequisites WHERE concept_id = $1 AND prerequisite_id = $2",
            concept_id, prerequisite_id,
        )
        return result == "DELETE 1"

    async def get_prerequisites(self, concept_id: UUID) -> list[UUID]:
        rows = await self._pool.fetch(
            "SELECT prerequisite_id FROM concept_prerequisites WHERE concept_id = $1",
            concept_id,
        )
        return [r["prerequisite_id"] for r in rows]

    async def get_all_prerequisites(self, course_id: UUID) -> dict[UUID, list[UUID]]:
        rows = await self._pool.fetch(
            """
            SELECT cp.concept_id, cp.prerequisite_id
            FROM concept_prerequisites cp
            JOIN concepts c ON c.id = cp.concept_id
            WHERE c.course_id = $1
            """,
            course_id,
        )
        result: dict[UUID, list[UUID]] = {}
        for r in rows:
            result.setdefault(r["concept_id"], []).append(r["prerequisite_id"])
        return result

    # --- Mastery ---

    async def get_mastery(
        self, student_id: UUID, concept_id: UUID
    ) -> ConceptMastery | None:
        row = await self._pool.fetchrow(
            "SELECT id, student_id, concept_id, mastery, updated_at FROM concept_mastery WHERE student_id = $1 AND concept_id = $2",
            student_id, concept_id,
        )
        return self._to_mastery(row) if row else None

    async def get_course_mastery(
        self, student_id: UUID, course_id: UUID
    ) -> list[tuple[Concept, float]]:
        rows = await self._pool.fetch(
            """
            SELECT c.id, c.course_id, c.lesson_id, c.name, c.description,
                   c.parent_id, c."order", c.created_at,
                   COALESCE(cm.mastery, 0.0) as mastery
            FROM concepts c
            LEFT JOIN concept_mastery cm ON cm.concept_id = c.id AND cm.student_id = $1
            WHERE c.course_id = $2
            ORDER BY c."order", c.created_at
            """,
            student_id, course_id,
        )
        return [(self._to_concept(r), r["mastery"]) for r in rows]

    async def upsert_mastery(
        self, student_id: UUID, concept_id: UUID, mastery: float
    ) -> ConceptMastery:
        clamped = max(0.0, min(1.0, mastery))
        row = await self._pool.fetchrow(
            """
            INSERT INTO concept_mastery (student_id, concept_id, mastery, updated_at)
            VALUES ($1, $2, $3, now())
            ON CONFLICT (student_id, concept_id)
            DO UPDATE SET mastery = $3, updated_at = now()
            RETURNING id, student_id, concept_id, mastery, updated_at
            """,
            student_id, concept_id, clamped,
        )
        return self._to_mastery(row)

    @staticmethod
    def _to_concept(row: asyncpg.Record) -> Concept:
        return Concept(
            id=row["id"],
            course_id=row["course_id"],
            lesson_id=row["lesson_id"],
            name=row["name"],
            description=row["description"],
            parent_id=row["parent_id"],
            order=row["order"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_mastery(row: asyncpg.Record) -> ConceptMastery:
        return ConceptMastery(
            id=row["id"],
            student_id=row["student_id"],
            concept_id=row["concept_id"],
            mastery=row["mastery"],
            updated_at=row["updated_at"],
        )
