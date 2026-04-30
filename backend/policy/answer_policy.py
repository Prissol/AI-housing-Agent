from __future__ import annotations

from typing import Any

from policy.question_builder import build_clarification_questions


def evaluate_answer_policy(
    extracted_data: dict[str, Any],
    required_fields: list[str],
    confidence_scores: dict[str, float],
    confidence_threshold: float,
    max_questions: int = 3,
    answered_question_ids: list[str] | None = None,
) -> dict[str, Any]:
    missing_fields: list[str] = []
    uncertain_fields: list[str] = []
    answered_qids = set(answered_question_ids or [])

    stairs = extracted_data.get("stairs", [])
    exits = extracted_data.get("exits", [])
    corridors = extracted_data.get("corridors", [])
    rooms = extracted_data.get("rooms", [])
    dimensions = extracted_data.get("dimensions", [])

    field_has_value = {
        "stairs.width_ft": any(item.get("width_ft") is not None for item in stairs),
        "exits.width_ft": any(item.get("width_ft") is not None for item in exits),
        "corridors.width_ft": any(item.get("width_ft") is not None for item in corridors),
        "rooms.area_sqft": any(item.get("area_sqft") is not None for item in rooms),
        "dimensions.unit": any(str(item.get("unit") or "").strip() for item in dimensions),
    }

    for field in required_fields:
        qid = field.replace(".", "_")
        if qid in answered_qids and field_has_value.get(field, False):
            continue
        if not field_has_value.get(field, False):
            missing_fields.append(field)

    confidence_to_field = {
        "rooms": "rooms.area_sqft",
        "dimensions": "dimensions.unit",
        "circulation": "corridors.width_ft",
    }
    for key, score in confidence_scores.items():
        mapped = confidence_to_field.get(str(key))
        if not mapped:
            continue
        qid = mapped.replace(".", "_")
        # Prevent clarification loops after user has explicitly provided value.
        if qid in answered_qids and field_has_value.get(mapped, False):
            continue
        if float(score or 0.0) < confidence_threshold:
            uncertain_fields.append(mapped)

    uncertain_fields = list(dict.fromkeys(uncertain_fields))

    needs_clarification = bool(missing_fields or uncertain_fields)
    questions = build_clarification_questions(
        missing_fields=missing_fields,
        uncertain_fields=uncertain_fields,
        context={
            "source_file": extracted_data.get("source_file", ""),
            "source_mode": extracted_data.get("meta", {}).get("source_mode", ""),
            "answered_question_ids": answered_question_ids or [],
        },
        max_questions=max_questions,
    )
    return {
        "allow_final_answer": not needs_clarification,
        "status": "READY_FOR_DECISION" if not needs_clarification else "NEEDS_CLARIFICATION",
        "missing_fields": missing_fields,
        "uncertain_fields": uncertain_fields,
        "questions": questions,
    }
