"""Relationship routes."""

import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.relationship_repo import RelationshipRepository
from app.schemas.relationship import RelationshipResponse, RelationshipListResponse, GraphResponse
from app.services.graph_service import GraphService
from app.services.case_access_service import require_case_access

router = APIRouter(prefix="/cases/{case_id}/relationships", tags=["Relationships"])


@router.get("", response_model=RelationshipListResponse)
async def list_relationships(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all relationships for a case."""
    await require_case_access(db, user, case_id)
    repo = RelationshipRepository(db)
    items = await repo.get_for_case(case_id)
    return RelationshipListResponse(
        items=[RelationshipResponse.model_validate(r) for r in items],
        total=len(items),
    )


@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the network graph for a case."""
    await require_case_access(db, user, case_id)
    service = GraphService(db)
    return await service.build_and_analyze(case_id)


@router.get("/graph/global", response_model=GraphResponse)
async def get_global_graph(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the global network graph across all cases."""
    service = GraphService(db)
    return await service.build_and_analyze(None)
