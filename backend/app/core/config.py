"""Centralized configuration for APEX LINK."""

from typing import Literal

ALGORITHM_VERSION = "1.0.0"

# Analysis scoring weights — stored here so every consumer references the same values.
KEY_ENTITY_WEIGHTS = {
    "degree": 0.40,
    "betweenness": 0.40,
    "cross_case": 0.20,
}

CROSS_CASE_WEIGHTS = {
    "phone_exact": 30,
    "upi_exact": 25,
    "email_exact": 20,
    "ip_exact": 15,
    "device_exact": 20,
    "vehicle_exact": 15,
    "location_proximity": 10,
    "temporal_proximity": 10,
}

# Entity types that use deterministic (exact-match) resolution.
DETERMINISTIC_ENTITY_TYPES = [
    "PHONE",
    "EMAIL",
    "IP_ADDRESS",
    "UPI_ID",
    "URL",
]

# Suspicious pattern thresholds — configurable, not scattered.
SUSPICIOUS_PATTERNS = {
    "bridge": {
        "description": "An entity connects otherwise separated clusters.",
        "min_separated_clusters": 2,
    },
    "multi_case": {
        "description": "An identifier appears across many cases.",
        "min_cases": 3,
    },
    "burst": {
        "description": "Many events involving the same entity within a short time window.",
        "window_hours": 24,
        "min_events": 10,
    },
    "fan_out": {
        "description": "One source connects to unusually many recipients.",
        "min_recipients": 8,
    },
    "fan_in": {
        "description": "Many entities converge on one target.",
        "min_sources": 8,
    },
    "shared_infrastructure": {
        "description": "Multiple cases share infrastructure indicators.",
        "min_cases": 2,
    },
}

# Allowed evidence MIME types for uploads.
ALLOWED_EVIDENCE_MIME_TYPES = {
    "DOCUMENT": [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/csv",
    ],
    "IMAGE": [
        "image/jpeg",
        "image/png",
        "image/webp",
    ],
    "AUDIO": [
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
    ],
    "VIDEO": [
        "video/mp4",
        "video/webm",
    ],
    "REPORT": [
        "application/pdf",
        "text/plain",
    ],
    "CDR": ["text/csv"],
    "TRANSACTION": ["text/csv"],
    "SURVEILLANCE_NOTE": ["text/plain", "text/csv"],
    "OTHER": [],  # fallback — handled separately
}

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

EvidenceType = Literal[
    "DOCUMENT",
    "IMAGE",
    "AUDIO",
    "VIDEO",
    "REPORT",
    "CDR",
    "TRANSACTION",
    "SURVEILLANCE_NOTE",
    "OTHER",
]

EntityType = Literal[
    "PERSON",
    "PHONE",
    "EMAIL",
    "IP_ADDRESS",
    "UPI_ID",
    "BANK_ACCOUNT",
    "VEHICLE",
    "DEVICE",
    "LOCATION",
    "ORGANIZATION",
    "SOCIAL_ACCOUNT",
    "URL",
    "CASE_REFERENCE",
]
