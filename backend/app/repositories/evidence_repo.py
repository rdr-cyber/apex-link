"""Evidence repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, db: AsyncSession):
        super().__init__(Evidence, db)

    async def get_by_case(
        self, case_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> tuple[Sequence[Evidence], int]:
        count_result = await self.db.execute(
            select(func.count(Evidence.id)).where(Evidence.case_id == case_id)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Evidence)
            .where(Evidence.case_id == case_id)
            .order_by(desc(Evidence.created_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def get_by_evidence_number(self, evidence_number: str) -> Evidence | None:
        result = await self.db.execute(
            select(Evidence).where(Evidence.evidence_number == evidence_number)
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count(Evidence.id)))
        return result.scalar_one()
