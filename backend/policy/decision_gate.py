from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = [
    "stairs.width_ft",
    "exits.width_ft",
    "corridors.width_ft",
    "rooms.area_sqft",
    "dimensions.unit",
]


def _has_field(extracted_data: dict[str, Any], field: str) -> bool:
    if field == "stairs.width_ft":
        return any(item.get("width_ft") is not None for item in extracted_data.get("stairs", []))
    if field == "exits.width_ft":
        return any(item.get("width_ft") is not None for item in extracted_data.get("exits", []))
    if field == "corridors.width_ft":
        return any(item.get("width_ft") is not None for item in extracted_data.get("corridors", []))
    if field == "rooms.area_sqft":
        return any(item.get("area_sqft") is not None for item in extracted_data.get("rooms", []))
    if field == "dimensions.unit":
        return any(str(item.get("unit") or "").strip() for item in extracted_data.get("dimensions", []))
    return False


def apply_decision_gate(
    extracted_data: dict[str, Any],
    confidence_scores: dict[str, float],
    confidence_threshold: float,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    fields = required_fields or REQUIRED_FIELDS
    missing_fields = [field for field in fields if not _has_field(extracted_data, field)]
    low_confidence_fields = [k for k, v in confidence_scores.items() if float(v or 0.0) < confidence_threshold]
    if missing_fields or low_confidence_fields:
        return {
            "allow_final_answer": False,
            "status": "NEEDS_CLARIFICATION",
            "missing_fields": missing_fields,
            "uncertain_fields": low_confidence_fields,
            "confidence_label": "low",
        }
    return {
        "allow_final_answer": True,
        "status": "READY_FOR_DECISION",
        "missing_fields": [],
        "uncertain_fields": [],
        "confidence_label": "high",
    }
