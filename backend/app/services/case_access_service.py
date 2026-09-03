"""Case-level authorization service.

Provides centralized access-control checks for all resources
associated with cases.

Access policy:
- ADMIN: can access all cases
- INVESTIGATOR: cases they created or are assigned to
- ANALYST: cases they are assigned to (read-only)

This is a prototype-grade implementation. Production deployments
would use organization/tenant scoping.
"""

import uuid
from typing import Sequence

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.user import User, UserRole


async def _get_user_case_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """Get IDs of cases the user can access."""
    if user.role == UserRole.ADMIN:
        # Admin can access all cases
        result = await db.execute(select(Case.id))
        return {row[0] for row in result.all()}

    # Investigator/Analyst: cases they created or are assigned to
    stmt = select(Case.id).where(
        or_(
            Case.created_by == user.id,
            Case.assigned_to == user.id,
        )
    )
    result = await db.execute(stmt)
    return {row[0] for row in result.all()}


async def can_view_case(db: AsyncSession, user: User, case_id: uuid.UUID) -> bool:
    """Check if user can view a specific case."""
    if user.role == UserRole.ADMIN:
        return True
    case_ids = await _get_user_case_ids(db, user)
    return case_id in case_ids


async def can_edit_case(db: AsyncSession, user: User, case: Case) -> bool:
    """Check if user can edit a case."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.INVESTIGATOR:
        return case.created_by == user.id or case.assigned_to == user.id
    return False


async def can_analyze_case(db: AsyncSession, user: User, case_id: uuid.UUID) -> bool:
    """Check if user can run analysis on a case (same as view for prototype)."""
    return await can_view_case(db, user, case_id)


async def get_accessible_case_ids(db: AsyncSession, user: User) -> set[uuid.UUID]:
    """Get all case IDs accessible to the user."""
    return await _get_user_case_ids(db, user)


async def require_case_access(db: AsyncSession, user: User, case_id: uuid.UUID) -> None:
    """Raise 404 if user cannot access the case.

    Uses 404 instead of 403 to prevent case-ID enumeration.
    """
    from fastapi import HTTPException, status

    if not await can_view_case(db, user, case_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found.",
        )


async def require_case_edit(db: AsyncSession, user: User, case: Case) -> None:
    """Raise 403 if user cannot edit the case."""
    from fastapi import HTTPException, status

    if not await can_edit_case(db, user, case):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this case.",
        )


async def can_access_entity(db: AsyncSession, user: User, entity_id: uuid.UUID) -> bool:
    """Check if user can access an entity (via associated case)."""
    from app.models.entity import CaseEntity

    if user.role == UserRole.ADMIN:
        return True

    # Find cases associated with this entity
    stmt = (
        select(CaseEntity.case_id)
        .where(CaseEntity.entity_id == entity_id)
        .distinct()
    )
    result = await db.execute(stmt)
    entity_case_ids = {row[0] for row in result.all()}

    if not entity_case_ids:
        return True  # Entity not linked to any case — allow access

    user_case_ids = await _get_user_case_ids(db, user)
    return bool(entity_case_ids & user_case_ids)


async def require_entity_access(db: AsyncSession, user: User, entity_id: uuid.UUID) -> None:
    """Raise 404 if user cannot access the entity's cases."""
    from fastapi import HTTPException, status

    if not await can_access_entity(db, user, entity_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
        )
