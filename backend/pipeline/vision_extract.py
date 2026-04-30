from __future__ import annotations

from typing import Any, Dict, List

from pipeline.preprocess import Tile
from schemas.extracted import OCRBlock
from services.openai_client import OpenAIClient


def _ocr_hint_for_tile(tile_id: str, ocr_blocks: List[OCRBlock]) -> str:
    return "\n".join(block.text for block in ocr_blocks if block.tile_id == tile_id)


def _validate_and_repair(payload: Dict[str, Any]) -> Dict[str, Any]:
    expected_lists = ["floors", "rooms", "stairs", "lifts", "exits", "corridors", "dimensions"]
    repaired = dict(payload or {})
    for key in expected_lists:
        if not isinstance(repaired.get(key), list):
            repaired[key] = []
    confidence = repaired.get("confidence")
    if not isinstance(confidence, dict):
        confidence = {}
    repaired["confidence"] = {
        "floors": float(confidence.get("floors", 0.0) or 0.0),
        "rooms": float(confidence.get("rooms", 0.0) or 0.0),
        "circulation": float(confidence.get("circulation", 0.0) or 0.0),
        "dimensions": float(confidence.get("dimensions", 0.0) or 0.0),
    }
    repaired["explanation"] = str(repaired.get("explanation", ""))
    return repaired


def extract_vision_structured(tiles: List[Tile], ocr_blocks: List[OCRBlock], client: OpenAIClient) -> List[Dict[str, Any]]:
    responses: List[Dict[str, Any]] = []
    for tile in tiles:
        payload = _validate_and_repair(client.extract_structured(tile.path.read_bytes(), _ocr_hint_for_tile(tile.tile_id, ocr_blocks)))
        payload["tile_id"] = tile.tile_id
        payload["page_index"] = tile.page_index
        payload["coords"] = {"x1": tile.coords[0], "y1": tile.coords[1], "x2": tile.coords[2], "y2": tile.coords[3]}
        responses.append(payload)
    return responses
