"""Lead repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, db: AsyncSession):
        super().__init__(Lead, db)

    async def get_for_case(self, case_id: uuid.UUID) -> Sequence[Lead]:
        result = await self.db.execute(
            select(Lead).where(Lead.case_id == case_id).order_by(desc(Lead.score))
        )
        return result.scalars().all()

    async def search(
        self,
        case_id: uuid.UUID | None = None,
        priority: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
        skip: int = 0,
        limit: int = 20,
        accessible_case_ids: set | None = None,
    ) -> tuple[Sequence[Lead], int]:
        stmt = select(Lead)
        count_stmt = select(func.count(Lead.id))

        if accessible_case_ids is not None:
            stmt = stmt.where(Lead.case_id.in_(accessible_case_ids))
            count_stmt = count_stmt.where(Lead.case_id.in_(accessible_case_ids))

        if case_id:
            stmt = stmt.where(Lead.case_id == case_id)
            count_stmt = count_stmt.where(Lead.case_id == case_id)

        if priority:
            stmt = stmt.where(Lead.priority == priority)
            count_stmt = count_stmt.where(Lead.priority == priority)

        if status:
            stmt = stmt.where(Lead.status == status)
            count_stmt = count_stmt.where(Lead.status == status)

        if min_score is not None:
            stmt = stmt.where(Lead.score >= min_score)
            count_stmt = count_stmt.where(Lead.score >= min_score)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        result = await self.db.execute(stmt.order_by(desc(Lead.score)).offset(skip).limit(limit))
        return result.scalars().all(), total

    async def count_high_priority(self) -> int:
        result = await self.db.execute(
            select(func.count(Lead.id)).where(Lead.priority.in_(["HIGH", "CRITICAL"]))
        )
        return result.scalar_one()
