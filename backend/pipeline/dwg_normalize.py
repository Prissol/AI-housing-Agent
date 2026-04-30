from __future__ import annotations

from typing import Any, Dict


UNIT_TO_FEET = {
    "mm": 0.00328084,
    "cm": 0.0328084,
    "m": 3.28084,
    "ft": 1.0,
    "feet": 1.0,
    "in": 0.0833333,
    "inch": 0.0833333,
    "drawing_unit": 1.0,
}


def _to_feet(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    factor = UNIT_TO_FEET.get(str(unit).lower(), 1.0)
    return float(value) * factor


def normalize_dwg_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    drawing_units = list(payload.get("units_detected", []))
    primary_unit = drawing_units[0] if drawing_units else "drawing_unit"
    normalized = {
        "drawing_id": str(payload.get("drawing_id", "")),
        "units_detected": drawing_units or ["drawing_unit"],
        "scale_info": dict(payload.get("scale_info", {})),
        "floors": list(payload.get("floors", [])),
        "rooms": list(payload.get("rooms", [])),
        "stairs": list(payload.get("stairs", [])),
        "lifts": list(payload.get("lifts", [])),
        "exits": list(payload.get("exits", [])),
        "corridors": list(payload.get("corridors", [])),
        "dimensions": list(payload.get("dimensions", [])),
        "confidence_scores": {
            "floors": 0.0,
            "rooms": 0.0,
            "circulation": 0.0,
            "dimensions": 0.0,
            "overall": 0.0,
        },
        "unresolved_fields": list(payload.get("unresolved_fields", [])),
        "meta": dict(payload.get("meta", {})),
    }

    for key in ["stairs", "exits", "corridors"]:
        for item in normalized[key]:
            item_unit = str(item.get("unit") or primary_unit or "drawing_unit")
            item["width_ft"] = _to_feet(item.get("width_ft"), item_unit)
            item["source_type"] = str(item.get("source_type") or "GEOMETRY_INFERRED")
            item["layer_name"] = str(item.get("layer_name") or item.get("source_trace", {}).get("layer") or "0")
            item["source_entity_ids"] = list(item.get("source_entity_ids") or ([item.get("source_trace", {}).get("entity_id")] if item.get("source_trace", {}).get("entity_id") else []))

    for room in normalized["rooms"]:
        if room.get("area_sqft") is not None:
            room_unit = str(room.get("unit") or primary_unit or "drawing_unit")
            room["area_sqft"] = _to_feet(float(room["area_sqft"]), room_unit)
        room["source_type"] = str(room.get("source_type") or "GEOMETRY_INFERRED")
        room["layer_name"] = str(room.get("layer_name") or room.get("source_trace", {}).get("layer") or "0")
        room["source_entity_ids"] = list(room.get("source_entity_ids") or ([room.get("source_trace", {}).get("entity_id")] if room.get("source_trace", {}).get("entity_id") else []))

    for dim in normalized["dimensions"]:
        dim_unit = str(dim.get("unit") or primary_unit or "drawing_unit").lower()
        dim["value"] = _to_feet(dim.get("value"), dim_unit)
        dim["unit"] = "ft"
        dim["source_type"] = str(dim.get("source_type") or "CAD_DIM")
        dim["source_entity_id"] = str(dim.get("source_entity_id") or (dim.get("source_trace") or {}).get("entity_id") or "")
        dim["source_entity_ids"] = list(dim.get("source_entity_ids") or ([dim["source_entity_id"]] if dim["source_entity_id"] else []))
        dim["layer_name"] = str(dim.get("layer_name") or (dim.get("source_trace") or {}).get("layer") or "0")

    parser_conf = float(normalized["meta"].get("parser_confidence", 0.0) or 0.0)
    incoming_scores = dict(payload.get("confidence_scores", {}))
    normalized["confidence_scores"] = {
        "floors": float(incoming_scores.get("floors", parser_conf) or parser_conf),
        "rooms": float(incoming_scores.get("rooms", parser_conf) or parser_conf),
        "circulation": float(incoming_scores.get("circulation", parser_conf) or parser_conf),
        "dimensions": float(incoming_scores.get("dimensions", parser_conf) or parser_conf),
        "overall": float(incoming_scores.get("overall", parser_conf) or parser_conf),
    }
    normalized["confidence"] = {
        "floors": normalized["confidence_scores"]["floors"],
        "rooms": normalized["confidence_scores"]["rooms"],
        "circulation": normalized["confidence_scores"]["circulation"],
        "dimensions": normalized["confidence_scores"]["dimensions"],
    }
    if normalized["confidence_scores"]["overall"] < 0.85:
        normalized["unresolved_fields"] = list(dict.fromkeys(normalized["unresolved_fields"] + ["LOW_CONFIDENCE"]))
    return normalized
