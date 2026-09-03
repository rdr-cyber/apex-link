"""Explanation service — generates human-readable explanations for analytical results.

Every explanation must be grounded in stored facts.
No explanation may invent relationships not supported by data.
"""

import json
from typing import Any


def explain_correlation(
    score: float,
    factors: list[dict],
    shared_entity_count: int,
) -> dict[str, Any]:
    """Generate a structured explanation for a cross-case correlation.

    Returns machine-readable and human-readable explanation.
    """
    # Build factor summary
    factor_descriptions = []
    supporting_evidence = set()

    for f in factors:
        etype = f.get("entity_type", "unknown")
        display = f.get("display_value", "unknown")
        weight = f.get("weight", 0)
        readable_type = f.get("type", "").replace("_", " ").replace("exact", "").strip()

        factor_descriptions.append({
            "label": f"Shared {readable_type}",
            "detail": f"{etype}: {display}",
            "weight_contribution": weight,
            "explanation": f"Same {readable_type} identifier '{display}' was found in both cases.",
        })

    # Generate human-readable text
    if score >= 75:
        strength = "strong"
    elif score >= 50:
        strength = "moderate"
    elif score >= 25:
        strength = "weak"
    else:
        strength = "minimal"

    reasons_text = "\n".join(
        f"• {fd['explanation']}" for fd in factor_descriptions
    ) or "• No matching identifiers found."

    human_readable = (
        f"Potential cross-case relationship detected ({strength} correlation).\n\n"
        f"Shared identifiers: {shared_entity_count}\n"
        f"Correlation score: {score}/100\n\n"
        f"Reasons:\n{reasons_text}\n\n"
        f"This result is an analytical lead requiring investigator review."
    )

    return {
        "score": score,
        "strength": strength,
        "factor_descriptions": factor_descriptions,
        "human_readable": human_readable,
        "supporting_evidence_ids": list(supporting_evidence),
    }


def explain_pattern(
    pattern_type: str,
    entity_info: dict,
    observed_value: Any,
    threshold: Any,
    supporting_cases: list[str] = None,
) -> str:
    """Generate human-readable explanation for a detected pattern."""
    entity_label = entity_info.get("display_value", "unknown")
    entity_type = entity_info.get("entity_type", "unknown")

    explanations = {
        "MULTI_CASE_IDENTIFIER": (
            f"The {entity_type.lower()} '{entity_label}' appears in "
            f"{observed_value} cases (threshold: {threshold}). "
            f"This may indicate a recurring identifier across investigations."
        ),
        "BRIDGE_ENTITY": (
            f"The {entity_type.lower()} '{entity_label}' connects "
            f"{observed_value} otherwise-separated network clusters "
            f"(threshold: {threshold}). This entity may be a structural bridge."
        ),
        "FAN_OUT": (
            f"The {entity_type.lower()} '{entity_label}' has "
            f"{observed_value} direct connections "
            f"(threshold: {threshold}). This may indicate broad activity."
        ),
        "FAN_IN": (
            f"The {entity_type.lower()} '{entity_label}' receives connections from "
            f"{observed_value} sources "
            f"(threshold: {threshold}). This may indicate convergence."
        ),
        "SHARED_INFRASTRUCTURE": (
            f"The {entity_type.lower()} '{entity_label}' is shared across "
            f"{observed_value} cases "
            f"(threshold: {threshold}). Multiple investigations reference this infrastructure."
        ),
    }

    base = explanations.get(
        pattern_type,
        f"Pattern '{pattern_type}' detected for {entity_type} '{entity_label}'."
    )

    if supporting_cases:
        base += f"\n\nRelated cases: {', '.join(supporting_cases)}"

    base += "\n\nThis result is an analytical observation requiring investigator review."

    return base
