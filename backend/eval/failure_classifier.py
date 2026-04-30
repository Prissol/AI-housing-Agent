from __future__ import annotations

from typing import Any


BUCKETS = [
    "PREPROCESS_QUALITY",
    "OCR_READ_ERROR",
    "UNIT_NORMALIZATION_ERROR",
    "ENTITY_MAPPING_ERROR",
    "DWG_PARSE_ERROR",
    "RULE_MAPPING_ERROR",
    "MISSING_EVIDENCE",
    "LOW_CONFIDENCE_SHOULD_BLOCK",
    "UNKNOWN",
]


def classify_failure(case_payload: dict[str, Any]) -> str:
    extracted = case_payload.get("extracted_data", {})
    summary = case_payload.get("summary", {})
    rule_results = case_payload.get("rule_results", [])
    source_file = str(extracted.get("source_file", "")).lower()
    confidence = extracted.get("confidence", {})
    ocr_blocks = extracted.get("ocr_blocks", [])
    dims = extracted.get("dimensions", [])

    if source_file.endswith(".dwg") or source_file.endswith(".dxf"):
        meta = extracted.get("meta", {})
        if "cad" in str(meta.get("source_mode", "")).lower() and not extracted.get("floors"):
            return "DWG_PARSE_ERROR"

    avg_conf = 0.0
    if isinstance(confidence, dict) and confidence:
        vals = [float(v or 0.0) for v in confidence.values()]
        avg_conf = sum(vals) / max(1, len(vals))
    if avg_conf < 0.8 and summary.get("passed", 0) > 0:
        return "LOW_CONFIDENCE_SHOULD_BLOCK"

    noisy = 0
    for block in ocr_blocks[:200]:
        text = str(block.get("text", "")).strip()
        if text and len(text) <= 2 and not any(ch.isdigit() for ch in text):
            noisy += 1
    if noisy > 80:
        return "OCR_READ_ERROR"

    if any(str(dim.get("unit", "")).lower() in {"mm", "cm", "m", "in"} and dim.get("value") for dim in dims):
        return "UNIT_NORMALIZATION_ERROR"

    if not extracted.get("stairs") or not extracted.get("exits") or not extracted.get("corridors"):
        return "MISSING_EVIDENCE"

    if any(item.get("status") == "needs_review" for item in rule_results) and extracted.get("rooms"):
        return "ENTITY_MAPPING_ERROR"

    if any(item.get("status") == "pass" and "insufficient" in str(item.get("reason", "")).lower() for item in rule_results):
        return "RULE_MAPPING_ERROR"

    if summary.get("needs_review", 0) > 0 and avg_conf < 0.5:
        return "PREPROCESS_QUALITY"

    return "UNKNOWN"
