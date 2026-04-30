from __future__ import annotations

import re
from typing import Any, Dict, List

from normalization.unit_normalizer import parse_dimension_to_feet


def _normalize_bbox(value: Any) -> Dict[str, float] | None:
    if isinstance(value, dict):
        return {
            "x": float(value.get("x", 0.0) or 0.0),
            "y": float(value.get("y", 0.0) or 0.0),
            "w": float(value.get("w", 0.0) or 0.0),
            "h": float(value.get("h", 0.0) or 0.0),
        }
    if isinstance(value, (list, tuple)) and len(value) == 4:
        x1, y1, x2, y2 = value
        x1f = float(x1 or 0.0)
        y1f = float(y1 or 0.0)
        x2f = float(x2 or 0.0)
        y2f = float(y2 or 0.0)
        return {"x": x1f, "y": y1f, "w": max(0.0, x2f - x1f), "h": max(0.0, y2f - y1f)}
    return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return parse_dimension_to_feet(value)


def _normalize_item_list(items: List[Dict[str, Any]], width_key: str = "width_ft", area_key: str = "area_sqft") -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        entry = dict(item)
        if width_key in entry:
            entry[width_key] = _as_float(entry.get(width_key))
        if area_key in entry:
            entry[area_key] = _as_float(entry.get(area_key))
        bbox_candidate = entry.get("bbox", entry.get("bounding_box"))
        if bbox_candidate is not None:
            entry["bbox"] = _normalize_bbox(bbox_candidate)
        if "floor" in entry and entry.get("floor") is not None:
            entry["floor"] = str(entry.get("floor"))
        signature = (
            entry.get("name"),
            entry.get(width_key),
            entry.get(area_key),
            str(entry.get("bbox", {})),
        )
        if signature in seen:
            continue
        seen.add(signature)
        normalized.append(entry)
    return normalized


def _first_numeric_dimension_by_label(dimensions: List[Dict[str, Any]], keywords: List[str]) -> float | None:
    for dim in dimensions:
        label = str(dim.get("label") or "").lower()
        if not any(keyword in label for keyword in keywords):
            continue
        value = parse_dimension_to_feet(dim.get("value"), str(dim.get("unit") or dim.get("units") or ""))
        if value is not None:
            return value
    return None


def _backfill_measurements_from_dimensions(merged: Dict[str, Any]) -> None:
    dimensions = merged.get("dimensions", [])
    if not dimensions:
        return

    stair_dim = _first_numeric_dimension_by_label(dimensions, ["stair", "staircase"])
    exit_dim = _first_numeric_dimension_by_label(dimensions, ["exit", "egress", "door"])
    corridor_dim = _first_numeric_dimension_by_label(dimensions, ["corridor", "passage", "hall"])
    room_area_dim = _first_numeric_dimension_by_label(dimensions, ["room", "bed", "area", "sqft", "sq ft"])

    for item in merged.get("stairs", []):
        if item.get("width_ft") is None and stair_dim is not None:
            item["width_ft"] = stair_dim
    for item in merged.get("exits", []):
        if item.get("width_ft") is None and exit_dim is not None:
            item["width_ft"] = exit_dim
    for item in merged.get("corridors", []):
        if item.get("width_ft") is None and corridor_dim is not None:
            item["width_ft"] = corridor_dim
    for item in merged.get("rooms", []):
        if item.get("area_sqft") is None and room_area_dim is not None:
            item["area_sqft"] = room_area_dim


def normalize_extracted(vision_parts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "drawing_id": "",
        "units_detected": [],
        "scale_info": {},
        "floors": [],
        "rooms": [],
        "stairs": [],
        "lifts": [],
        "exits": [],
        "corridors": [],
        "dimensions": [],
        "confidence_scores": {"floors": 0.0, "rooms": 0.0, "circulation": 0.0, "dimensions": 0.0, "overall": 0.0},
        "unresolved_fields": [],
        "confidence": {"floors": 0.0, "rooms": 0.0, "circulation": 0.0, "dimensions": 0.0},
        "meta": {"tiles_processed": len(vision_parts)},
    }
    confidences = []
    for part in vision_parts:
        for key in ["floors", "rooms", "stairs", "lifts", "exits", "corridors", "dimensions"]:
            merged[key].extend(part.get(key, []) or [])
        confidences.append(part.get("confidence", {}))

    merged["rooms"] = _normalize_item_list(merged["rooms"], width_key="width_ft", area_key="area_sqft")
    merged["stairs"] = _normalize_item_list(merged["stairs"], width_key="width_ft", area_key="area_sqft")
    merged["exits"] = _normalize_item_list(merged["exits"], width_key="width_ft", area_key="area_sqft")
    merged["corridors"] = _normalize_item_list(merged["corridors"], width_key="width_ft", area_key="area_sqft")
    merged["lifts"] = _normalize_item_list(merged["lifts"], width_key="width_ft", area_key="area_sqft")
    merged["floors"] = _normalize_item_list(merged["floors"], width_key="width_ft", area_key="area_sqft")

    for dim in merged["dimensions"]:
        if "label" not in dim:
            dim["label"] = str(dim.get("name") or dim.get("text") or "unknown")
        if "unit" not in dim and "units" in dim:
            dim["unit"] = dim.get("units")
        unit = str(dim.get("unit") or "ft").lower()
        dim["value"] = parse_dimension_to_feet(dim.get("value"), unit)
        dim["unit"] = "ft"
        dim_bbox = dim.get("bbox", dim.get("bounding_box"))
        dim["bbox"] = _normalize_bbox(dim_bbox)

    _backfill_measurements_from_dimensions(merged)

    if confidences:
        for key in merged["confidence"].keys():
            vals = [float(c.get(key, 0.0) or 0.0) for c in confidences]
            merged["confidence"][key] = sum(vals) / max(1, len(vals))
    merged["confidence_scores"] = {
        "floors": merged["confidence"]["floors"],
        "rooms": merged["confidence"]["rooms"],
        "circulation": merged["confidence"]["circulation"],
        "dimensions": merged["confidence"]["dimensions"],
        "overall": sum(float(v or 0.0) for v in merged["confidence"].values()) / max(1, len(merged["confidence"])),
    }
    return merged
