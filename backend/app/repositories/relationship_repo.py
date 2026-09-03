"""Relationship repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relationship import Relationship
from app.repositories.base import BaseRepository


class RelationshipRepository(BaseRepository[Relationship]):
    def __init__(self, db: AsyncSession):
        super().__init__(Relationship, db)

    async def get_for_case(self, case_id: uuid.UUID) -> Sequence[Relationship]:
        result = await self.db.execute(
            select(Relationship).where(Relationship.case_id == case_id).order_by(desc(Relationship.created_at))
        )
        return result.scalars().all()

    async def count_for_case(self, case_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Relationship.id)).where(Relationship.case_id == case_id)
        )
        return result.scalar_one()

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count(Relationship.id)))
        return result.scalar_one()

    async def find_existing(
        self,
        source_entity_id: uuid.UUID,
        target_entity_id: uuid.UUID,
        relationship_type: str,
        case_id: uuid.UUID,
    ) -> Relationship | None:
        result = await self.db.execute(
            select(Relationship).where(
                Relationship.source_entity_id == source_entity_id,
                Relationship.target_entity_id == target_entity_id,
                Relationship.relationship_type == relationship_type,
                Relationship.case_id == case_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_graph(self) -> Sequence[Relationship]:
        result = await self.db.execute(select(Relationship))
        return result.scalars().all()

    async def get_cross_case_relationships(self) -> Sequence[dict]:
        """Find entities that appear in multiple cases."""
        stmt = (
            select(
                Relationship.source_entity_id,
                Relationship.target_entity_id,
                func.count(func.distinct(Relationship.case_id)).label("case_count"),
            )
            .group_by(Relationship.source_entity_id, Relationship.target_entity_id)
            .having(func.count(func.distinct(Relationship.case_id)) > 1)
        )
        result = await self.db.execute(stmt)
        return [dict(row._mapping) for row in result.all()]
