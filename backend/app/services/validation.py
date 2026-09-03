"""Entity validation service.

Validates extracted entities before persistence.
Invalid values are rejected — not silently stored as normalized entities.
Where rejection would lose useful forensic context, retain the raw mention
separately but do not convert it into a normalized entity.
"""

import re
from ipaddress import ip_address

# Indian mobile numbers start with 6, 7, 8, or 9
_PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")

# Common UPI provider suffixes
_UPI_PROVIDERS = {
    "ybl", "paytm", "okicici", "okaxis", "oksbi", "payu", "phonepe",
    "gpay", "amazonpay", "freecharge", "mobikwik", "irctc", "bajaj",
    "kvb", "iomoney", "_slice", "jio", "airtel", "vi", "npci",
}


def is_valid_phone(normalized: str) -> bool:
    """Check if a normalized value is a valid Indian mobile number."""
    return bool(_PHONE_PATTERN.match(normalized))


def is_valid_email(normalized: str) -> bool:
    """Basic email validation after normalization."""
    if not normalized or "@" not in normalized:
        return False
    parts = normalized.split("@")
    if len(parts) != 2:
        return False
    local, domain = parts
    if not local or not domain:
        return False
    if "." not in domain:
        return False
    return True


def is_valid_ip(normalized: str) -> bool:
    """Validate using Python's ipaddress module."""
    try:
        addr = ip_address(normalized)
        return addr.version == 4
    except ValueError:
        return False


def is_valid_upi(normalized: str) -> bool:
    """Validate UPI format: identifier@provider."""
    if "@" not in normalized:
        return False
    parts = normalized.split("@")
    if len(parts) != 2:
        return False
    local, provider = parts
    if not local or not provider:
        return False
    # Provider should be alphabetic and reasonable length
    if not provider.isalpha() or len(provider) > 20:
        return False
    return True


def is_valid_url(normalized: str) -> bool:
    """Basic URL validation."""
    return normalized.startswith("http://") or normalized.startswith("https://")


def is_valid_vehicle(normalized: str) -> bool:
    """Validate Indian vehicle registration format.

    Format: 2 letters + 1-2 digits + 1-2 letters + 4 digits
    Example: WB12AB1234, DL01AA1234
    """
    return bool(re.match(r"^[A-Z]{2}\d{1,2}[A-Z]{1,2}\d{4}$", normalized))


def validate_entity(entity_type: str, normalized_value: str) -> tuple[bool, str]:
    """Validate a normalized entity value.

    Returns (is_valid, reason).
    """
    validators = {
        "PHONE": lambda v: (is_valid_phone(v), "Not a valid 10-digit Indian mobile number"),
        "EMAIL": lambda v: (is_valid_email(v), "Not a valid email address"),
        "IP_ADDRESS": lambda v: (is_valid_ip(v), "Not a valid IPv4 address"),
        "UPI_ID": lambda v: (is_valid_upi(v), "Not a valid UPI ID (expected identifier@provider)"),
        "URL": lambda v: (is_valid_url(v), "Not a valid URL"),
        "VEHICLE": lambda v: (is_valid_vehicle(v), "Not a valid Indian vehicle registration"),
    }
    validator = validators.get(entity_type)
    if validator:
        return validator(normalized_value)
    # For PERSON, ORGANIZATION, LOCATION, DEVICE — accept if non-empty
    return bool(normalized_value.strip()), "Empty value"
