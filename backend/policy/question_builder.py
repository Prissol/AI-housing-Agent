from __future__ import annotations

from typing import Any


def _modality_label(context: dict[str, Any]) -> str:
    source_mode = str(context.get("source_mode", "")).lower()
    source_file = str(context.get("source_file", "")).lower()
    if source_file.endswith(".dwg") or source_file.endswith(".dxf") or "cad" in source_mode:
        return "CAD drawing"
    if source_file.endswith(".pdf"):
        return "PDF plan"
    return "image plan"


def build_clarification_questions(
    missing_fields: list[str],
    uncertain_fields: list[str],
    context: dict[str, Any],
    max_questions: int = 3,
) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    modality = _modality_label(context)
    previously_answered = set(str(item) for item in (context.get("answered_question_ids") or []))

    mapping = {
        "stairs.width_ft": f"{modality}: confirm stair clear width (examples: 3'-6\", 4 ft, 1200 mm).",
        "exits.width_ft": f"{modality}: confirm exit/door clear width near lobby or stair.",
        "corridors.width_ft": f"{modality}: confirm minimum corridor clear width.",
        "rooms.area_sqft": f"{modality}: confirm minimum room area value from the plan.",
        "dimensions.unit": f"{modality}: confirm drawing unit (ft, m, mm, or cm).",
        "rooms": f"{modality}: room labels/areas are unclear. Confirm key room names with area.",
        "dimensions": f"{modality}: dimensions are unclear. Confirm one measurable dimension with unit.",
        "circulation": f"{modality}: circulation path is unclear. Confirm stair/exit/corridor measurements.",
    }

    seen_fields: set[str] = set()
    for field in missing_fields + uncertain_fields:
        if len(questions) >= max_questions:
            break
        if field in seen_fields:
            continue
        seen_fields.add(field)
        prompt = mapping.get(field, f"Please clarify value for {field}.")
        qid = field.replace(".", "_")
        if qid in previously_answered:
            prompt = f"{prompt} Previous answer was not enough; please provide a numeric value with unit."
        questions.append(
            {
                "question_id": qid,
                "field": field,
                "question": prompt,
            }
        )
    return questions[:max_questions]
