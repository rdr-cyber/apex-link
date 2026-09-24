"""Case management service."""

import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseStatus, CasePriority
from app.repositories.case_repo import CaseRepository
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse


class CaseService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = CaseRepository(db)

    async def _generate_case_number(self) -> str:
        """Generate the next case number: AL-YYYY-NNNN."""
        import datetime
        year = datetime.datetime.now(datetime.timezone.utc).year
        # Count existing cases this year to generate next number
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.count(Case.id)).where(Case.case_number.like(f"AL-{year}-%"))
        )
        count = result.scalar_one()
        return f"AL-{year}-{count + 1:04d}"

    async def create_case(self, data: CaseCreate, created_by: uuid.UUID) -> CaseResponse:
        """Create a new case."""
        case_number = await self._generate_case_number()
        # Validate priority
        try:
            priority = CasePriority(data.priority)
        except ValueError:
            priority = CasePriority.MEDIUM

        case = await self.repo.create(
            case_number=case_number,
            title=data.title,
            description=data.description,
            category=data.category,
            priority=priority,
            incident_date=data.incident_date,
            location=data.location,
            created_by=created_by,
            assigned_to=data.assigned_to,
        )
        return CaseResponse.model_validate(case)

    async def get_case(self, case_id: uuid.UUID) -> CaseResponse:
        """Get a case by ID."""
        case = await self.repo.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        return CaseResponse.model_validate(case)

    async def update_case(self, case_id: uuid.UUID, data: CaseUpdate) -> CaseResponse:
        """Update a case."""
        case = await self.repo.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

        update_data = data.model_dump(exclude_unset=True)

        # Validate enums if provided
        if "priority" in update_data and update_data["priority"] is not None:
            update_data["priority"] = CasePriority(update_data["priority"])
        if "status" in update_data and update_data["status"] is not None:
            update_data["status"] = CaseStatus(update_data["status"])

        case = await self.repo.update(case, **update_data)
        return CaseResponse.model_validate(case)

    async def list_cases(
        self,
        query: str | None = None,
        case_status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
        accessible_case_ids: set[uuid.UUID] | None = None,
    ) -> CaseListResponse:
        """List cases with filtering and pagination."""
        skip = (page - 1) * page_size
        cases, total = await self.repo.search(
            query=query,
            status=case_status,
            priority=priority,
            category=category,
            skip=skip,
            limit=page_size,
            accessible_case_ids=accessible_case_ids,
        )
        return CaseListResponse(
            items=[CaseResponse.model_validate(c) for c in cases],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete_case(self, case_id: uuid.UUID) -> None:
        """Delete a case."""
        case = await self.repo.get_by_id(case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        await self.repo.delete(case)
