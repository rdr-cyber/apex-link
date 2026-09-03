"""Models package — import all models so Alembic and SQLAlchemy can discover them."""

from app.models.user import User, UserRole
from app.models.case import Case, CaseStatus, CasePriority
from app.models.evidence import Evidence, EvidenceType
from app.models.entity import Entity, EntityType, CaseEntity
from app.models.entity_mention import EntityMention
from app.models.relationship import Relationship, RelationshipType
from app.models.lead import Lead, LeadStatus, LeadPriority
from app.models.audit import AuditLog
from app.models.analysis_result import AnalysisResult

__all__ = [
    "User",
    "UserRole",
    "Case",
    "CaseStatus",
    "CasePriority",
    "Evidence",
    "EvidenceType",
    "Entity",
    "EntityType",
    "CaseEntity",
    "EntityMention",
    "Relationship",
    "RelationshipType",
    "Lead",
    "LeadStatus",
    "LeadPriority",
    "AuditLog",
    "AnalysisResult",
]
