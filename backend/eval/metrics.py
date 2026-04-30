from __future__ import annotations

from typing import Any


def _required_field_present(extracted_data: dict[str, Any], field: str) -> bool:
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


def compute_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    required = ["stairs.width_ft", "exits.width_ft", "corridors.width_ft", "rooms.area_sqft", "dimensions.unit"]
    total_slots = len(cases) * len(required)
    filled = 0
    clarification = 0
    false_pass = 0
    success = 0
    for case in cases:
        extracted = case.get("extracted_data", {})
        for field in required:
            if _required_field_present(extracted, field):
                filled += 1
        status = case.get("status", "READY_FOR_DECISION")
        if status == "NEEDS_CLARIFICATION":
            clarification += 1
        summary = case.get("summary", {})
        needs_review = int(summary.get("needs_review", 0) or 0)
        failed = int(summary.get("failed", 0) or 0)
        passed = int(summary.get("passed", 0) or 0)
        if status == "READY_FOR_DECISION" and passed > 0 and failed == 0 and needs_review > 0:
            false_pass += 1
        if status == "READY_FOR_DECISION" and failed == 0 and needs_review == 0:
            success += 1

    extraction_field_accuracy = (filled / total_slots) if total_slots else 0.0
    total = len(cases)
    return {
        "extraction_field_accuracy": round(extraction_field_accuracy, 4),
        "critical_rule_precision": None,  # requires labels
        "critical_rule_recall": None,  # requires labels
        "false_pass_rate": round((false_pass / total), 4) if total else 0.0,
        "needs_clarification_rate": round((clarification / total), 4) if total else 0.0,
        "overall_case_success_rate": round((success / total), 4) if total else 0.0,
        "labeled_eval": False,
    }
