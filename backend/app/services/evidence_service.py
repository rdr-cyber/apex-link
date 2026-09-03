"""Evidence management service — upload, storage, integrity verification."""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import MAX_UPLOAD_SIZE_BYTES, ALLOWED_EVIDENCE_MIME_TYPES
from app.core.settings import get_settings
from app.models.evidence import Evidence, EvidenceType
from app.repositories.evidence_repo import EvidenceRepository

settings = get_settings()


class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EvidenceRepository(db)

    async def _generate_evidence_number(self) -> str:
        """Generate unique evidence number: EV-NNNNN."""
        from sqlalchemy import select, func
        result = await self.db.execute(select(func.count(Evidence.id)))
        count = result.scalar_one()
        return f"EV-{count + 1:05d}"

    def _calculate_sha256(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    # Allowed file extensions by evidence type
    ALLOWED_EXTENSIONS = {
        'DOCUMENT': {'.pdf', '.doc', '.docx', '.txt', '.csv', '.rtf'},
        'IMAGE': {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'},
        'AUDIO': {'.mp3', '.wav', '.ogg', '.m4a', '.flac'},
        'VIDEO': {'.mp4', '.webm', '.avi', '.mov'},
        'REPORT': {'.pdf', '.txt', '.doc', '.docx'},
        'CDR': {'.csv', '.xlsx'},
        'TRANSACTION': {'.csv', '.xlsx'},
        'SURVEILLANCE_NOTE': {'.txt', '.csv'},
        'OTHER': set(),  # allow any
    }

    def _validate_file(self, file: UploadFile, evidence_type: EvidenceType) -> None:
        """Validate file type, extension, and size."""
        if file.size and file.size > MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        # Validate file extension
        ext = Path(file.filename or "").suffix.lower()
        allowed = self.ALLOWED_EXTENSIONS.get(evidence_type.value, set())
        if allowed and ext not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not allowed for evidence type '{evidence_type.value}'. "
                       f"Allowed: {', '.join(sorted(allowed))}",
            )

    async def upload_evidence(
        self,
        case_id: uuid.UUID,
        file: UploadFile,
        evidence_type: EvidenceType,
        description: str = "",
        source: str = "unknown",
        collected_by: str | None = None,
    ) -> Evidence:
        """Upload and store evidence with hash verification.

        In 'metadata_only' storage mode (production on ephemeral filesystems),
        the file content is read and hashed for integrity, but only the metadata
        is persisted. The binary file is NOT saved to local disk.
        """
        self._validate_file(file, evidence_type)

        # Read file content
        content = await file.read()
        sha256_hash = self._calculate_sha256(content)

        storage_mode = settings.STORAGE_MODE
        storage_path = ""

        if storage_mode == "local":
            # Generate safe filename
            safe_filename = hashlib.md5(f"{uuid.uuid4()}_{file.filename}".encode()).hexdigest()
            ext = Path(file.filename or "unknown").suffix
            safe_filename = f"{safe_filename}{ext}"

            # Determine storage path
            storage_dir = Path(settings.LOCAL_STORAGE_PATH) / str(case_id)
            storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = str(storage_dir / safe_filename)

            # Save file
            with open(storage_path, "wb") as f:
                f.write(content)
        else:
            # metadata_only mode: hash recorded, binary not persisted locally
            storage_path = f"metadata_only://{case_id}/{file.filename}"

        # Create evidence record
        evidence_number = await self._generate_evidence_number()
        evidence = await self.repo.create(
            case_id=case_id,
            evidence_number=evidence_number,
            evidence_type=evidence_type,
            filename=file.filename or "unknown",
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
            storage_path=storage_path,
            sha256_hash=sha256_hash,
            description=description,
            source=source,
            collected_by=collected_by,
            collected_at=datetime.now(timezone.utc),
        )

        return evidence

    async def verify_integrity(self, evidence_id: uuid.UUID) -> dict:
        """Verify evidence integrity by comparing stored and current hashes."""
        evidence = await self.repo.get_by_id(evidence_id)
        if evidence is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found.")

        # Metadata-only mode: binary file not available for re-verification
        if evidence.storage_path.startswith("metadata_only://"):
            return {
                "evidence_id": str(evidence.id),
                "stored_hash": evidence.sha256_hash,
                "current_hash": "",
                "integrity_status": "METADATA_ONLY",
            }

        try:
            with open(evidence.storage_path, "rb") as f:
                current_hash = self._calculate_sha256(f.read())
            status_text = "VERIFIED" if current_hash == evidence.sha256_hash else "MISMATCH"
        except FileNotFoundError:
            current_hash = ""
            status_text = "UNAVAILABLE"

        return {
            "evidence_id": str(evidence.id),
            "stored_hash": evidence.sha256_hash,
            "current_hash": current_hash,
            "integrity_status": status_text,
        }
