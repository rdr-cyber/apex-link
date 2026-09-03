"""API v1 router — combines all route modules."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.entities import router as entities_router
from app.api.v1.relationships import router as relationships_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.leads import router as leads_router
from app.api.v1.reports import router as reports_router
from app.api.v1.audit import router as audit_router
from app.api.v1.search import router as search_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.correlations import router as correlations_router
from app.api.v1.timeline import router as timeline_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.analysis_history import router as analysis_history_router
from app.api.v1.entity_management import router as entity_mgmt_router
from app.api.v1.intelligence import router as intelligence_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(cases_router)
api_router.include_router(evidence_router)
api_router.include_router(entities_router)
api_router.include_router(entity_mgmt_router)
api_router.include_router(relationships_router)
api_router.include_router(analysis_router)
api_router.include_router(leads_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)
api_router.include_router(search_router)
api_router.include_router(dashboard_router)
api_router.include_router(correlations_router)
api_router.include_router(timeline_router)
api_router.include_router(ingestion_router)
api_router.include_router(analysis_history_router)
api_router.include_router(intelligence_router)
