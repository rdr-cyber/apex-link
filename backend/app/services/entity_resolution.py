"""Entity resolution — determines whether two mentions refer to the same entity.

Deterministic types use exact normalized match.
Person names use conservative similarity only.
"""

from difflib import SequenceMatcher

from app.core.config import DETERMINISTIC_ENTITY_TYPES


def is_deterministic_match(entity_type: str, value_a: str, value_b: str) -> bool:
    """Check if two normalized values are an exact match for deterministic entity types."""
    if entity_type in DETERMINISTIC_ENTITY_TYPES:
        return value_a.strip().lower() == value_b.strip().lower()
    return False


def compute_name_similarity(name_a: str, name_b: str) -> float:
    """Compute similarity between two person names.

    Returns a score between 0 and 1.
    Very conservative — only high similarity scores are returned.
    """
    a = name_a.strip().lower()
    b = name_b.strip().lower()

    if a == b:
        return 1.0

    # SequenceMatcher ratio
    ratio = SequenceMatcher(None, a, b).ratio()

    # Boost if one is a prefix of the other (e.g., "Rahul Kumar" vs "Rahul K.")
    if a.startswith(b) or b.startswith(a):
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        prefix_ratio = shorter / longer
        ratio = max(ratio, prefix_ratio * 0.95)

    # Boost for word-prefix matches (e.g., "rahul kumar" vs "rahul k.")
    a_words = a.split()
    b_words = b.split()
    if len(a_words) >= 1 and len(b_words) >= 1:
        # Check if all words of the shorter name are prefix-matched by the longer
        shorter_words = a_words if len(a_words) <= len(b_words) else b_words
        longer_words = b_words if len(a_words) <= len(b_words) else a_words
        matched = 0
        for sw in shorter_words:
            for lw in longer_words:
                clean_lw = lw.rstrip('.')
                if clean_lw.startswith(sw) or sw.startswith(clean_lw):
                    matched += 1
                    break
        if matched == len(shorter_words) and len(shorter_words) > 0:
            prefix_score = len(shorter_words) / max(len(longer_words), 1)
            ratio = max(ratio, 0.7 + prefix_score * 0.3)

    return round(ratio, 4)


def should_merge_entities(
    entity_type: str,
    normalized_a: str,
    normalized_b: str,
    name_similarity_threshold: float = 0.90,
) -> tuple[bool, float]:
    """Determine whether two entities should be merged.

    Returns (should_merge, confidence).
    For deterministic types: exact match → merge with high confidence.
    For person names: high similarity → possible match, confidence proportional to similarity.
    """
    if entity_type in DETERMINISTIC_ENTITY_TYPES:
        if is_deterministic_match(entity_type, normalized_a, normalized_b):
            return True, 1.0
        return False, 0.0

    # For non-deterministic types (PERSON, ORGANIZATION, etc.)
    if entity_type == "PERSON":
        sim = compute_name_similarity(normalized_a, normalized_b)
        if sim >= name_similarity_threshold:
            return True, sim * 0.85  # Reduce confidence — requires review
        return False, sim

    # For LOCATION, ORGANIZATION — conservative exact match
    if normalized_a.strip().lower() == normalized_b.strip().lower():
        return True, 0.80

    return False, 0.0
