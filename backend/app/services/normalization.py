"""Centralized normalization rules for all entity types.

Every normalized entity preserves its original raw value.
Normalization never destroys source evidence wording.
"""

import re
from ipaddress import ip_address


def normalize_phone(raw: str) -> str:
    """Normalize an Indian phone number to 10 digits.

    Accepts: 9876543210, +91 9876543210, +91-9876543210, 09876543210
    Canonical: 9876543210
    """
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) > 10:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) > 10:
        digits = digits[1:]
    return digits[-10:] if len(digits) >= 10 else digits


def normalize_email(raw: str) -> str:
    """Normalize email: lowercase, strip whitespace.

    USER@EXAMPLE.COM → user@example.com
    """
    return raw.strip().lower()


def normalize_ip(raw: str) -> str | None:
    """Validate and normalize an IPv4 address.

    Uses Python's ipaddress for strict validation.
    Returns None if invalid.
    """
    try:
        addr = ip_address(raw.strip())
        if addr.version == 4:
            return str(addr)
        return None
    except ValueError:
        return None


def normalize_upi(raw: str) -> str:
    """Normalize UPI ID: lowercase, strip whitespace.

    Scammer@YBL → scammer@ybl
    """
    return raw.strip().lower()


def normalize_url(raw: str) -> str:
    """Normalize URL: lowercase, strip trailing slash, strip whitespace."""
    return raw.strip().rstrip("/").lower()


def normalize_vehicle(raw: str) -> str:
    """Normalize Indian vehicle number: uppercase, remove spaces/dashes.

    WB 12 AB 1234 → WB12AB1234
    """
    return re.sub(r"[\s\-]", "", raw).upper()


def normalize_device(raw: str) -> str:
    """Normalize device identifier: uppercase, strip whitespace."""
    return raw.strip().upper()


def normalize_text(raw: str) -> str:
    """Normalize freeform text: strip, collapse whitespace."""
    return re.sub(r"\s+", " ", raw.strip())


def normalize_entity_value(entity_type: str, raw: str) -> str | None:
    """Route to the appropriate normalizer for the given entity type.

    Returns None if the value cannot be normalized (invalid).
    """
    normalizers = {
        "PHONE": normalize_phone,
        "EMAIL": normalize_email,
        "IP_ADDRESS": normalize_ip,
        "UPI_ID": normalize_upi,
        "URL": normalize_url,
        "VEHICLE": normalize_vehicle,
        "DEVICE": normalize_device,
    }
    normalizer = normalizers.get(entity_type)
    if normalizer:
        return normalizer(raw)
    # For PERSON, ORGANIZATION, LOCATION, etc. — lowercase + strip
    return normalize_text(raw).lower()
