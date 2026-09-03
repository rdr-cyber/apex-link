"""Audit log repository."""

import uuid
from typing import Sequence

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def log(
        self,
        user_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: str = "",
        ip_address: str | None = None,
        case_id: uuid.UUID | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            case_id=case_id,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def search(
        self,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        case_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count(AuditLog.id))

        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
            count_stmt = count_stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
            count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)
        if case_id:
            stmt = stmt.where(AuditLog.case_id == case_id)
            count_stmt = count_stmt.where(AuditLog.case_id == case_id)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        result = await self.db.execute(stmt.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit))
        return result.scalars().all(), total
