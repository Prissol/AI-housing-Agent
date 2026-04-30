from typing import Any, Dict, Optional


def build_evidence(
    source: str,
    value: Any,
    required: Any,
    bbox: Optional[Dict[str, Any]] = None,
    floor: Optional[str] = None,
    tile_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "source": source,
        "observed_value": value,
        "required_value": required,
        "bbox": bbox or {},
        "floor": floor,
        "tile_id": tile_id,
    }


def merge_evidence(base: Dict[str, Any], source_items: list[dict[str, Any]]) -> Dict[str, Any]:
    evidence_points = []
    source_entity_ids = []
    source_layers = []
    for item in source_items:
        trace = item.get("source_trace") or {}
        if not trace:
            continue
        entity_id = trace.get("entity_id")
        layer = trace.get("layer")
        if entity_id:
            source_entity_ids.append(str(entity_id))
        if layer:
            source_layers.append(str(layer))
        evidence_points.append(
            {
                "source": trace.get("source", "unknown"),
                "entity_id": entity_id,
                "layer": layer,
                "value": item.get("width_ft") or item.get("area_sqft") or item.get("count"),
            }
        )
    if evidence_points:
        base["evidence_points"] = evidence_points
    if source_entity_ids:
        base["entity_ids"] = sorted(set(source_entity_ids))
    if source_layers:
        base["layers"] = sorted(set(source_layers))
    return base
