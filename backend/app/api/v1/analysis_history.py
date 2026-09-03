"""Analysis history routes."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.analysis_result import AnalysisResult
from app.models.user import User

router = APIRouter(prefix="/analysis", tags=["Analysis History"])


@router.get("/{analysis_id}")
async def get_analysis_result(
    analysis_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific analysis result by ID."""
    stmt = select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    result = await db.execute(stmt)
    analysis = result.scalar_one_or_none()

    if analysis is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    import json
    return {
        "id": str(analysis.id),
        "case_id": str(analysis.case_id),
        "executed_by": str(analysis.executed_by),
        "executed_at": analysis.executed_at.isoformat() if analysis.executed_at else None,
        "algorithm_version": analysis.algorithm_version,
        "configuration_version": analysis.configuration_version,
        "status": analysis.status,
        "result_summary": json.loads(analysis.result_summary) if analysis.result_summary else {},
    }


@router.get("/case/{case_id}/history")
async def get_analysis_history(
    case_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get analysis history for a case."""
    stmt = (
        select(AnalysisResult)
        .where(AnalysisResult.case_id == case_id)
        .order_by(desc(AnalysisResult.executed_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    analyses = result.scalars().all()

    import json
    return {
        "case_id": str(case_id),
        "analyses": [
            {
                "id": str(a.id),
                "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                "algorithm_version": a.algorithm_version,
                "status": a.status,
                "result_summary": json.loads(a.result_summary) if a.result_summary else {},
            }
            for a in analyses
        ],
        "total": len(analyses),
    }
