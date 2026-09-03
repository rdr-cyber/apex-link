"""Entity extraction service — rule-based + normalization + validation layer.

Layered approach:
  1. Rule-based extraction (regex)
  2. Normalization (via normalization.py)
  3. Validation (via validation.py)
  4. Confidence scoring
  5. Extraction method tracking

NLP (spaCy) is optional and only adds name/location extraction when available.
"""

import re
from typing import List

from app.schemas.entity import ExtractedEntity
from app.services.normalization import normalize_phone, normalize_email, normalize_ip, normalize_upi, normalize_url, normalize_vehicle, normalize_device
from app.services.validation import validate_entity

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------
_PHONE_RE = re.compile(
    r"(?:\+91[\s-]?)?(?:0)?([6-9][\d\s]{9,14})\b"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")
_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_UPI_RE = re.compile(r"[\w.\-]+@[a-zA-Z]+")
_VEHICLE_RE = re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,2}[\s-]?\d{4}\b")
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
)
_MONEY_RE = re.compile(r"(?:₹|INR|Rs\.?)\s*[\d,]+(?:\.\d{1,2})?")
_DEVICE_RE = re.compile(r"\b(?:IMEI[:\s]?\d{15}|MAC[:\s]?[0-9A-Fa-f:]{17}|[0-9A-Fa-f]{12,16})\b")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def extract_entities_from_text(text: str) -> List[ExtractedEntity]:
    """Extract and normalize entities from plain text.

    Returns a deduplicated list of ExtractedEntity.
    Uses centralized normalization and validation.
    """
    seen: set[tuple[str, str]] = set()
    results: List[ExtractedEntity] = []

    def _add(entity_type: str, raw: str, normalized: str, confidence: float):
        key = (entity_type, normalized)
        if key not in seen:
            # Validate before adding
            is_valid, _reason = validate_entity(entity_type, normalized)
            if not is_valid:
                return
            seen.add(key)
            results.append(
                ExtractedEntity(
                    entity_type=entity_type,
                    raw_text=raw,
                    normalized_value=normalized,
                    confidence=confidence,
                )
            )

    # Phones
    for m in _PHONE_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_phone(raw)
        _add("PHONE", raw, norm, 0.95)

    # Emails
    for m in _EMAIL_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_email(raw)
        _add("EMAIL", raw, norm, 0.98)

    # IPs
    for m in _IP_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_ip(raw)
        if norm:
            _add("IP_ADDRESS", raw, norm, 0.99)

    # URLs
    for m in _URL_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_url(raw)
        _add("URL", raw, norm, 0.95)

    # UPI
    for m in _UPI_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_upi(raw)
        _add("UPI_ID", raw, norm, 0.90)

    # Vehicle
    for m in _VEHICLE_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_vehicle(raw)
        _add("VEHICLE", raw, norm, 0.85)

    # Money (informational, not an entity type — skip entity creation)
    # Dates (informational, not an entity type — skip entity creation)

    # Device identifiers
    for m in _DEVICE_RE.finditer(text):
        raw = m.group(0)
        norm = normalize_device(raw)
        _add("DEVICE", raw, norm, 0.85)

    return results
