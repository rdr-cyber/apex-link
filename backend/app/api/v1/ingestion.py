"""CSV/structured data ingestion routes."""

import csv
import io
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.models.evidence import Evidence, EvidenceType
from app.models.entity import EntityType
from app.repositories.audit_repo import AuditLogRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.services.analysis_service import AnalysisService
from app.services.normalization import normalize_phone, normalize_email, normalize_ip, normalize_upi, normalize_vehicle

router = APIRouter(prefix="/cases/{case_id}/ingest", tags=["Ingestion"])

# Expected CSV column schemas
CDR_COLUMNS = {"timestamp", "caller", "receiver", "duration_seconds", "cell_id", "location"}
TRANSACTION_COLUMNS = {"timestamp", "sender", "receiver", "amount", "transaction_type", "reference", "location"}
INTELLIGENCE_COLUMNS = {"timestamp", "source", "subject", "entity", "description", "location"}

# Entity type mapping for CSV columns
COLUMN_ENTITY_MAP = {
    "caller": ("PHONE", normalize_phone),
    "receiver": ("PHONE", normalize_phone),
    "sender": ("PHONE", normalize_phone),
    "entity": None,  # Generic — detect type
    "subject": ("PERSON", None),
    "location": ("LOCATION", None),
}


def _detect_csv_type(headers: list[str]) -> str | None:
    """Detect CSV type from headers."""
    header_set = set(h.strip().lower().replace(" ", "_") for h in headers)
    if CDR_COLUMNS.issubset(header_set):
        return "CDR"
    if TRANSACTION_COLUMNS.issubset(header_set):
        return "TRANSACTION"
    if INTELLIGENCE_COLUMNS.issubset(header_set):
        return "INTELLIGENCE"
    return None


def _validate_row(row: dict, csv_type: str, row_num: int) -> str | None:
    """Validate a single CSV row. Returns error message or None."""
    if csv_type == "CDR":
        if not row.get("caller") and not row.get("receiver"):
            return f"Row {row_num}: Both caller and receiver are empty"
    elif csv_type == "TRANSACTION":
        if not row.get("sender") and not row.get("receiver"):
            return f"Row {row_num}: Both sender and receiver are empty"
        if row.get("amount"):
            try:
                float(row["amount"].replace(",", ""))
            except ValueError:
                return f"Row {row_num}: Invalid amount '{row['amount']}'"
    elif csv_type == "INTELLIGENCE":
        if not row.get("entity") and not row.get("subject"):
            return f"Row {row_num}: Both entity and subject are empty"
    return None


@router.post("/csv")
async def ingest_csv(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    csv_type: str = Form("auto"),
    request: Request = None,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Import structured CSV data (CDR, transactions, intelligence records).

    Validates schema, normalizes entities, creates entities and relationships.
    Returns import report with success/failure counts.
    """
    # Read CSV content
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except UnicodeDecodeError:
            raise HTTPException(status_code=422, detail="Cannot decode CSV file. Use UTF-8 or Latin-1 encoding.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV file has no headers.")

    # Auto-detect type
    if csv_type == "auto":
        csv_type = _detect_csv_type(reader.fieldnames)
        if csv_type is None:
            raise HTTPException(
                status_code=422,
                detail=f"Cannot auto-detect CSV type from headers: {reader.fieldnames}. "
                       f"Expected CDR, Transaction, or Intelligence format."
            )

    # Save as evidence
    import hashlib
    import os
    from pathlib import Path
    from app.core.settings import get_settings
    settings = get_settings()

    storage_dir = Path(settings.LOCAL_STORAGE_PATH) / str(case_id) / "csv"
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = hashlib.md5(f"{uuid.uuid4()}_{file.filename}".encode()).hexdigest() + ".csv"
    storage_path = str(storage_dir / safe_name)

    with open(storage_path, "w", encoding="utf-8") as f:
        f.write(text)

    sha256 = hashlib.sha256(content).hexdigest()

    ev_repo = EvidenceRepository(db)
    ev_count_result = await db.execute(
        __import__("sqlalchemy", fromlist=["func"]).select(
            __import__("sqlalchemy", fromlist=["func"]).func.count(Evidence.id)
        )
    )
    ev_count = ev_count_result.scalar_one()

    evidence = await ev_repo.create(
        case_id=case_id,
        evidence_number=f"EV-{ev_count + 1:05d}",
        evidence_type=EvidenceType.CDR if csv_type == "CDR" else EvidenceType.TRANSACTION if csv_type == "TRANSACTION" else EvidenceType.SURVEILLANCE_NOTE,
        filename=file.filename or "import.csv",
        mime_type="text/csv",
        size_bytes=len(content),
        storage_path=storage_path,
        sha256_hash=sha256,
        description=f"CSV import: {csv_type} ({file.filename})",
        source="csv_import",
        collected_by=user.full_name,
    )

    # Process rows
    analysis_service = AnalysisService(db)
    total_rows = 0
    successful_rows = 0
    failed_rows = 0
    errors = []

    for row_num, row in enumerate(reader, start=1):
        total_rows += 1

        # Validate
        error = _validate_row(row, csv_type, row_num)
        if error:
            failed_rows += 1
            errors.append(error)
            continue

        # Build text for entity extraction from the row
        text_parts = []
        for key, value in row.items():
            if value and value.strip():
                text_parts.append(f"{key}: {value}")

        if not text_parts:
            failed_rows += 1
            errors.append(f"Row {row_num}: No extractable data")
            continue

        row_text = ". ".join(text_parts)

        # Save row as individual text evidence
        row_dir = Path(settings.LOCAL_STORAGE_PATH) / str(case_id) / "csv_rows"
        row_dir.mkdir(parents=True, exist_ok=True)
        row_path = str(row_dir / f"row_{row_num:05d}.txt")
        with open(row_path, "w") as f:
            f.write(row_text)

        row_sha256 = hashlib.sha256(row_text.encode()).hexdigest()
        row_evidence = await ev_repo.create(
            case_id=case_id,
            evidence_number=f"EV-{ev_count + row_num + 1:05d}",
            evidence_type=EvidenceType.CDR if csv_type == "CDR" else EvidenceType.TRANSACTION if csv_type == "TRANSACTION" else EvidenceType.SURVEILLANCE_NOTE,
            filename=f"row_{row_num}.txt",
            mime_type="text/plain",
            size_bytes=len(row_text.encode()),
            storage_path=row_path,
            sha256_hash=row_sha256,
            description=f"CSV row {row_num} from {csv_type} import",
            source="csv_import",
            collected_by=user.full_name,
        )

        try:
            extraction = await analysis_service.extract_entities_from_evidence(
                row_evidence.id, case_id, extraction_method="IMPORT"
            )
            successful_rows += 1
        except Exception as e:
            failed_rows += 1
            errors.append(f"Row {row_num}: Extraction failed — {str(e)}")

    # Generate relationships for the case
    rel_count = await analysis_service.generate_relationships(case_id)

    # Audit log
    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CSV_INGESTED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"CSV {csv_type}: {total_rows} rows, {successful_rows} OK, {failed_rows} failed",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return {
        "evidence_id": str(evidence.id),
        "csv_type": csv_type,
        "total_rows": total_rows,
        "successful_rows": successful_rows,
        "failed_rows": failed_rows,
        "relationships_created": rel_count,
        "errors": errors[:20],  # Limit error output
    }
