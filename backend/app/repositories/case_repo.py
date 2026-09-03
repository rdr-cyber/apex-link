"""Case repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseStatus
from app.repositories.base import BaseRepository


class CaseRepository(BaseRepository[Case]):
    def __init__(self, db: AsyncSession):
        super().__init__(Case, db)

    async def get_by_case_number(self, case_number: str) -> Case | None:
        result = await self.db.execute(select(Case).where(Case.case_number == case_number))
        return result.scalar_one_or_none()

    async def search(
        self,
        query: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 20,
        accessible_case_ids: set | None = None,
    ) -> tuple[Sequence[Case], int]:
        stmt = select(Case)
        count_stmt = select(func.count(Case.id))

        if accessible_case_ids is not None:
            stmt = stmt.where(Case.id.in_(accessible_case_ids))
            count_stmt = count_stmt.where(Case.id.in_(accessible_case_ids))

        if query:
            search_filter = or_(
                Case.case_number.ilike(f"%{query}%"),
                Case.title.ilike(f"%{query}%"),
                Case.description.ilike(f"%{query}%"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        if status:
            stmt = stmt.where(Case.status == CaseStatus(status))
            count_stmt = count_stmt.where(Case.status == CaseStatus(status))

        if priority:
            stmt = stmt.where(Case.priority == priority)
            count_stmt = count_stmt.where(Case.priority == priority)

        if category:
            stmt = stmt.where(Case.category == category)
            count_stmt = count_stmt.where(Case.category == category)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.order_by(desc(Case.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        cases = result.scalars().all()

        return cases, total

    async def get_active_count(self) -> int:
        result = await self.db.execute(
            select(func.count(Case.id)).where(Case.status.in_([CaseStatus.OPEN, CaseStatus.UNDER_REVIEW, CaseStatus.ANALYSIS]))
        )
        return result.scalar_one()
