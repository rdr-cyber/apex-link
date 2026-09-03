"""Entity repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, CaseEntity
from app.repositories.base import BaseRepository


class EntityRepository(BaseRepository[Entity]):
    def __init__(self, db: AsyncSession):
        super().__init__(Entity, db)

    async def find_by_normalized(self, entity_type: str, normalized_value: str) -> Entity | None:
        result = await self.db.execute(
            select(Entity).where(
                Entity.entity_type == entity_type,
                Entity.normalized_value == normalized_value,
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        entity_type: str | None = None,
        normalized_value: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[Entity], int]:
        stmt = select(Entity)
        count_stmt = select(func.count(Entity.id))

        if query:
            # Search across canonical_value, display_value, and normalized_value
            search_filter = or_(
                Entity.canonical_value.ilike(f"%{query}%"),
                Entity.display_value.ilike(f"%{query}%"),
                Entity.normalized_value.ilike(f"%{query}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        if normalized_value:
            nv_filter = Entity.normalized_value == normalized_value
            stmt = stmt.where(nv_filter)
            count_stmt = count_stmt.where(nv_filter)

        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
            count_stmt = count_stmt.where(Entity.entity_type == entity_type)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        result = await self.db.execute(stmt.order_by(desc(Entity.created_at)).offset(skip).limit(limit))
        return result.scalars().all(), total

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count(Entity.id)))
        return result.scalar_one()

    async def get_for_case(self, case_id: uuid.UUID) -> list[dict]:
        """Get all entities linked to a case with their CaseEntity info."""
        stmt = (
            select(CaseEntity, Entity)
            .join(Entity, CaseEntity.entity_id == Entity.id)
            .where(CaseEntity.case_id == case_id)
            .order_by(desc(CaseEntity.created_at))
        )
        result = await self.db.execute(stmt)
        return [{"case_entity": ce, "entity": e} for ce, e in result.all()]


class CaseEntityRepository(BaseRepository[CaseEntity]):
    def __init__(self, db: AsyncSession):
        super().__init__(CaseEntity, db)

    async def get_by_case_and_entity(self, case_id: uuid.UUID, entity_id: uuid.UUID) -> CaseEntity | None:
        result = await self.db.execute(
            select(CaseEntity).where(
                CaseEntity.case_id == case_id,
                CaseEntity.entity_id == entity_id,
            )
        )
        return result.scalar_one_or_none()
