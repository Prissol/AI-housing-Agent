from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from core.logger import get_logger
from services.openai_client import OpenAIClient

logger = get_logger(__name__)


INSUNITS_MAP: dict[int, str] = {
    0: "unknown",
    1: "in",
    2: "ft",
    4: "mm",
    5: "cm",
    6: "m",
}

ABBR_TO_KIND = {
    "ST": "stair",
    "STAIR": "stair",
    "STR": "stair",
    "LFT": "lift",
    "LIFT": "lift",
    "ELEV": "lift",
    "EXIT": "exit",
    "EGR": "exit",
    "DOOR": "exit",
    "CORR": "corridor",
    "PASS": "corridor",
    "FLR": "floor",
}


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _num_from_text(text: str) -> float | None:
    m = re.search(r"(-?\d+(\.\d+)?)", text or "", flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _parse_dimension_text(text: str) -> tuple[float | None, str | None]:
    raw = str(text or "").strip().lower()
    # 4'-0", 3'-6", etc.
    feet_inches = re.search(r"(\d+)\s*['’]\s*-?\s*(\d+)?", raw)
    if feet_inches:
        feet = float(feet_inches.group(1))
        inches = float(feet_inches.group(2) or 0)
        return feet + (inches / 12.0), "ft"

    for unit in ["mm", "cm", "m", "ft", "feet", "in", "inch"]:
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*" + re.escape(unit), raw)
        if m:
            return _safe_float(m.group(1)), unit
    return None, None


def _polygon_area(points: list[tuple[float, float]]) -> float | None:
    if len(points) < 3:
        return None
    area = 0.0
    for idx, point in enumerate(points):
        x1, y1 = point
        x2, y2 = points[(idx + 1) % len(points)]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def _classify_label(text: str) -> str | None:
    upper = str(text or "").strip().upper()
    if not upper:
        return None
    if "FLOOR" in upper:
        return "floor"
    if any(token in upper for token in ["STAIR", "STAIRCASE"]):
        return "stair"
    if any(token in upper for token in ["LIFT", "ELEV"]):
        return "lift"
    if any(token in upper for token in ["EXIT", "EGRESS", "DOOR"]):
        return "exit"
    if any(token in upper for token in ["CORRIDOR", "PASSAGE", "HALL"]):
        return "corridor"
    if any(token in upper for token in ["ROOM", "BED", "LOUNGE", "KITCHEN", "BATH", "TOILET", "WC"]):
        return "room"
    if upper in ABBR_TO_KIND:
        return ABBR_TO_KIND[upper]
    return None


def _is_ambiguous_label(text: str) -> bool:
    token = str(text or "").strip().upper()
    if not token or len(token) > 12:
        return False
    if re.search(r"\d", token):
        return False
    return bool(re.fullmatch(r"[A-Z]+", token))


def _bbox_from_points(points: list[tuple[float, float]]) -> Dict[str, float] | None:
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {"x": min(xs), "y": min(ys), "w": max(xs) - min(xs), "h": max(ys) - min(ys)}


def parse_dxf_entities(dxf_path: Path) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "drawing_id": dxf_path.stem,
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
        "meta": {
            "cad_source": str(dxf_path),
            "parser": "dxf_direct",
            "parser_stage_logs": [{"stage": "cad_parse", "status": "started"}],
        },
    }
    try:
        import ezdxf  # type: ignore
    except Exception as exc:  # pragma: no cover
        logger.warning("ezdxf unavailable for CAD parsing: %s", exc)
        payload["meta"]["parser_error"] = "ezdxf not installed."
        payload["meta"]["parser_confidence"] = 0.0
        payload["unresolved_fields"] = ["CAD_PARSE_FAIL"]
        return payload

    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception as exc:  # pragma: no cover
        payload["meta"]["parser_error"] = f"Failed to parse DXF: {exc}"
        payload["meta"]["parser_confidence"] = 0.0
        payload["unresolved_fields"] = ["CAD_PARSE_FAIL"]
        return payload

    msp = doc.modelspace()
    entity_count = 0
    hits = {"floors": 0, "rooms": 0, "circulation": 0, "dimensions": 0}
    layer_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)
    ambiguous_labels: list[str] = []
    ambiguous_lookup: dict[str, dict[str, Any]] = {}
    unit_hints: set[str] = set()
    insunits_code = int(getattr(doc.header, "$INSUNITS", 0) or 0)
    insunits_name = INSUNITS_MAP.get(insunits_code, "unknown")
    if insunits_name != "unknown":
        payload["units_detected"].append(insunits_name)
    payload["scale_info"] = {
        "insunits_code": insunits_code,
        "insunits_name": insunits_name,
        "modelspace_name": str(getattr(msp, "dxftype", lambda: "MODELSPACE")()),
    }

    def add_room(entry: dict[str, Any]) -> None:
        payload["rooms"].append(entry)
        hits["rooms"] += 1

    def add_circulation(bucket: str, entry: dict[str, Any]) -> None:
        payload[bucket].append(entry)
        hits["circulation"] += 1

    for entity in msp:
        entity_count += 1
        etype = entity.dxftype()
        type_counts[etype] += 1
        layer = str(getattr(entity.dxf, "layer", "0") or "0")
        layer_counts[layer] += 1
        handle = str(getattr(entity.dxf, "handle", ""))

        if etype in {"TEXT", "MTEXT"}:
            raw = getattr(entity.dxf, "text", None) or getattr(entity, "plain_text", lambda: "")() or getattr(entity, "text", "")
            text = str(raw or "").strip()
            if not text:
                continue
            source_trace = {"source": "CAD_TEXT", "entity_id": handle, "layer": layer, "text": text}
            point = getattr(entity.dxf, "insert", None)
            location = {"x": _safe_float(getattr(point, "x", None)), "y": _safe_float(getattr(point, "y", None))}

            label_kind = _classify_label(text)
            parsed_value, parsed_unit = _parse_dimension_text(text)
            if parsed_unit:
                unit_hints.add(parsed_unit.lower())

            if label_kind == "floor":
                payload["floors"].append(
                    {
                        "name": text,
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    }
                )
                hits["floors"] += 1
            elif label_kind == "stair":
                add_circulation(
                    "stairs",
                    {
                        "name": text,
                        "width_ft": parsed_value,
                        "unit": parsed_unit or "drawing_unit",
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    },
                )
            elif label_kind == "lift":
                payload["lifts"].append(
                    {
                        "name": text,
                        "count": 1,
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    }
                )
                hits["circulation"] += 1
            elif label_kind == "exit":
                add_circulation(
                    "exits",
                    {
                        "name": text,
                        "width_ft": parsed_value,
                        "unit": parsed_unit or "drawing_unit",
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    },
                )
            elif label_kind == "corridor":
                add_circulation(
                    "corridors",
                    {
                        "name": text,
                        "width_ft": parsed_value,
                        "unit": parsed_unit or "drawing_unit",
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    },
                )
            elif label_kind == "room":
                add_room(
                    {
                        "name": text,
                        "area_sqft": parsed_value,
                        "unit": parsed_unit or "drawing_unit",
                        "source_type": "CAD_TEXT",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                        "location": location,
                    }
                )
            elif _is_ambiguous_label(text):
                ambiguous_labels.append(text)
                ambiguous_lookup[text] = {"entity_id": handle, "layer": layer, "text": text, "location": location}

            val = parsed_value
            if val is not None:
                payload["dimensions"].append(
                    {
                        "label": text[:120],
                        "value": val,
                        "unit": parsed_unit or "drawing_unit",
                        "source_type": "CAD_TEXT",
                        "source_entity_id": handle,
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": source_trace,
                    }
                )
                hits["dimensions"] += 1

        elif etype in {"LWPOLYLINE", "POLYLINE"}:
            points = []
            try:
                points = [(float(p[0]), float(p[1])) for p in entity.get_points()]  # type: ignore[attr-defined]
            except Exception:
                points = []
            bbox = _bbox_from_points(points)
            closed = bool(getattr(entity, "closed", False))
            if bbox and ("ROOM" in layer.upper() or "SPACE" in layer.upper()):
                area_raw = _polygon_area(points) if closed else None
                add_room(
                    {
                        "name": layer,
                        "bbox": bbox,
                        "boundary": [{"x": pt[0], "y": pt[1]} for pt in points[:200]],
                        "area_sqft": area_raw,
                        "unit": "drawing_unit",
                        "source_type": "GEOMETRY_INFERRED",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "geometry_ref": {"entity_id": handle, "layer": layer},
                        "source_trace": {"source": "GEOMETRY_INFERRED", "entity_id": handle, "layer": layer},
                    }
                )
            if bbox and ("CORR" in layer.upper() or "PASS" in layer.upper()):
                add_circulation(
                    "corridors",
                    {
                        "name": layer,
                        "bbox": bbox,
                        "source_type": "GEOMETRY_INFERRED",
                        "source_entity_ids": [handle],
                        "layer_name": layer,
                        "source_trace": {"source": "GEOMETRY_INFERRED", "entity_id": handle, "layer": layer},
                    },
                )

        elif etype == "DIMENSION":
            measurement = getattr(entity.dxf, "actual_measurement", None)
            value = float(measurement) if measurement is not None else None
            if value is not None:
                hits["dimensions"] += 1
            payload["dimensions"].append(
                {
                    "label": f"DIM-{handle}",
                    "value": value,
                    "unit": "drawing_unit",
                    "source_type": "CAD_DIM",
                    "source_entity_id": handle,
                    "source_entity_ids": [handle],
                    "layer_name": layer,
                    "source_trace": {"source": "CAD_DIM", "entity_id": handle, "layer": layer},
                }
            )
        elif etype in {"LINE", "ARC", "CIRCLE", "INSERT"}:
            # Explicitly handled for stage traceability.
            continue

    if ambiguous_labels:
        ai_client = OpenAIClient()
        ai_result = ai_client.interpret_cad_labels(ambiguous_labels)
        for item in ai_result.get("mappings", []):
            label = str(item.get("label", "")).strip()
            mapped_type = str(item.get("mapped_type", "")).strip().lower()
            confidence = _safe_float(item.get("confidence")) or 0.0
            ref = ambiguous_lookup.get(label)
            if not ref or confidence < 0.85:
                continue
            entry = {
                "name": label,
                "source_type": "CAD_TEXT",
                "source_entity_ids": [ref["entity_id"]],
                "layer_name": ref["layer"],
                "source_trace": {"source": "CAD_TEXT", "entity_id": ref["entity_id"], "layer": ref["layer"], "ai_mapped": True},
                "location": ref.get("location") or {},
            }
            if mapped_type == "stair":
                add_circulation("stairs", entry)
            elif mapped_type == "exit":
                add_circulation("exits", entry)
            elif mapped_type == "corridor":
                add_circulation("corridors", entry)
            elif mapped_type == "lift":
                payload["lifts"].append({**entry, "count": 1})
                hits["circulation"] += 1
            elif mapped_type == "room":
                add_room(entry)
            elif mapped_type == "floor":
                payload["floors"].append(entry)
                hits["floors"] += 1

        unresolved_ai = [str(label) for label in ai_result.get("unresolved", []) if str(label).strip()]
        if unresolved_ai:
            payload["meta"]["ambiguous_labels"] = unresolved_ai[:40]
            payload["unresolved_fields"].append("LABEL_AMBIGUOUS")

    if unit_hints:
        payload["units_detected"] = list(dict.fromkeys(payload["units_detected"] + sorted(unit_hints)))

    floors_score = min(1.0, len(payload["floors"]) / 2.0)
    rooms_score = min(1.0, len(payload["rooms"]) / 4.0)
    circulation_count = len(payload["stairs"]) + len(payload["exits"]) + len(payload["corridors"])
    circulation_score = min(1.0, circulation_count / 4.0)
    dimensions_score = min(1.0, len(payload["dimensions"]) / 5.0)
    overall = round((floors_score + rooms_score + circulation_score + dimensions_score) / 4.0, 4)
    confidence = min(1.0, overall)
    payload["meta"]["entity_count"] = entity_count
    payload["meta"]["entity_type_counts"] = dict(type_counts)
    payload["meta"]["layer_counts"] = dict(layer_counts)
    payload["meta"]["parser_confidence"] = confidence
    payload["meta"]["parser_stage_logs"].append({"stage": "cad_parse", "status": "completed", "entity_count": entity_count})
    payload["confidence_scores"] = {
        "floors": floors_score,
        "rooms": rooms_score,
        "circulation": circulation_score,
        "dimensions": dimensions_score,
        "overall": confidence,
    }
    if len(payload["units_detected"]) > 1:
        payload["unresolved_fields"].append("UNIT_MISMATCH")
    if dimensions_score < 0.25:
        payload["unresolved_fields"].append("DIMENSION_MISSING")
    payload["unresolved_fields"] = list(dict.fromkeys(payload["unresolved_fields"]))
    return payload
