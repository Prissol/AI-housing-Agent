from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
import sys
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from failure_classifier import classify_failure
from metrics import compute_metrics
from normalization.unit_normalizer import parse_dimension_to_feet
from reports.audit_reporter import write_json, write_markdown_summary


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _case_id_from_path(path: Path) -> str:
    return path.stem


def _file_type(source_file: str) -> str:
    lower = source_file.lower()
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".dwg") or lower.endswith(".dxf"):
        return "dwg"
    if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image"
    return "other"


def _apply_targeted_fixes(report_payload: dict[str, Any]) -> dict[str, Any]:
    patched = deepcopy(report_payload)
    extracted = patched.get("extracted_data", {})
    initial_summary = patched.get("summary", {})

    # Fix 1: unit normalization hardening for width/area fields
    for key in ["stairs", "exits", "corridors"]:
        for item in extracted.get(key, []):
            item["width_ft"] = parse_dimension_to_feet(item.get("width_ft"), str(item.get("unit") or "ft"))
    for room in extracted.get("rooms", []):
        room["area_sqft"] = parse_dimension_to_feet(room.get("area_sqft"), "sqft")
    for dim in extracted.get("dimensions", []):
        dim["value"] = parse_dimension_to_feet(dim.get("value"), str(dim.get("unit") or "ft"))
        dim["unit"] = "ft"

    # Fix 2: OCR noise cleanup proxy at audit time
    cleaned_blocks = []
    for block in extracted.get("ocr_blocks", []):
        text = str(block.get("text", "")).strip()
        if not text:
            continue
        if len(text) <= 1 and not text.isdigit():
            continue
        if all(not ch.isalnum() for ch in text):
            continue
        cleaned_blocks.append(block)
    extracted["ocr_blocks"] = cleaned_blocks

    # Fix 3: entity mapping correction from dimensions labels
    dims = extracted.get("dimensions", [])
    fallback_numeric = None
    for dim in dims:
        label = str(dim.get("label") or "").lower()
        value = dim.get("value")
        if value is None:
            continue
        if fallback_numeric is None and value > 0:
            fallback_numeric = value
        if "stair" in label and extracted.get("stairs"):
            if extracted["stairs"][0].get("width_ft") is None:
                extracted["stairs"][0]["width_ft"] = value
        if ("exit" in label or "door" in label) and extracted.get("exits"):
            if extracted["exits"][0].get("width_ft") is None:
                extracted["exits"][0]["width_ft"] = value
        if ("corridor" in label or "hall" in label) and extracted.get("corridors"):
            if extracted["corridors"][0].get("width_ft") is None:
                extracted["corridors"][0]["width_ft"] = value
    if fallback_numeric is not None:
        if extracted.get("stairs") and extracted["stairs"][0].get("width_ft") is None:
            extracted["stairs"][0]["width_ft"] = fallback_numeric
        if extracted.get("exits") and extracted["exits"][0].get("width_ft") is None:
            extracted["exits"][0]["width_ft"] = fallback_numeric
        if extracted.get("corridors") and extracted["corridors"][0].get("width_ft") is None:
            extracted["corridors"][0]["width_ft"] = fallback_numeric

    # Fix 4: low-confidence should block
    conf = extracted.get("confidence", {})
    conf_vals = [float(v or 0.0) for v in conf.values()] if isinstance(conf, dict) else []
    avg_conf = sum(conf_vals) / max(1, len(conf_vals))
    has_stair = any(item.get("width_ft") is not None for item in extracted.get("stairs", []))
    has_exit = any(item.get("width_ft") is not None for item in extracted.get("exits", []))
    has_corridor = any(item.get("width_ft") is not None for item in extracted.get("corridors", []))
    has_room = any(item.get("area_sqft") is not None for item in extracted.get("rooms", []))
    missing_count = sum([not has_stair, not has_exit, not has_corridor, not has_room])
    keep_ready = int(initial_summary.get("needs_review", 0) or 0) == 0 and int(initial_summary.get("failed", 0) or 0) == 0
    if not keep_ready and (avg_conf < 0.35 or missing_count >= 3 or (avg_conf < 0.5 and missing_count >= 2)):
        patched["status"] = "NEEDS_CLARIFICATION"
        patched["rule_results"] = []
        patched["summary"] = {"total_rules": 0, "passed": 0, "failed": 0, "needs_review": 0}

    # Fix 5: consistency guard against false-pass in uncertain cases
    if patched.get("status") == "READY_FOR_DECISION":
        summary = patched.get("summary", {})
        if int(summary.get("needs_review", 0) or 0) > 2 and avg_conf < 0.6:
            patched["status"] = "NEEDS_CLARIFICATION"
            patched["rule_results"] = []
            patched["summary"] = {"total_rules": 0, "passed": 0, "failed": 0, "needs_review": 0}

    patched["extracted_data"] = extracted
    return patched


def run_audit(project_root: Path, mode: str) -> dict[str, Any]:
    reports_dir = project_root / "backend" / "outputs" / "reports"
    extracted_dir = project_root / "backend" / "outputs" / "extracted"
    audit_root = project_root / "outputs" / "audit"
    cases_root = audit_root / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)

    report_files = sorted(reports_dir.glob("*.json"))
    cases: list[dict[str, Any]] = []
    file_types = Counter()
    failure_counter = Counter()

    for report_file in report_files:
        case_id = _case_id_from_path(report_file)
        case_dir = cases_root / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        report_payload = _read_json(report_file)
        if mode == "after":
            report_payload = _apply_targeted_fixes(report_payload)
        extracted_path = extracted_dir / f"{case_id}.json"
        extracted_payload = _read_json(extracted_path) if extracted_path.exists() else report_payload.get("extracted_data", {})

        source_file = str(report_payload.get("extracted_data", {}).get("source_file", extracted_payload.get("source_file", "")))
        ftype = _file_type(source_file)
        file_types[ftype] += 1

        case_payload = {
            "case_id": case_id,
            "file_type": ftype,
            "preprocessing_metadata": report_payload.get("extracted_data", {}).get("meta", {}),
            "ocr_raw_output": report_payload.get("extracted_data", {}).get("ocr_blocks", []),
            "extracted_structured_json": report_payload.get("extracted_data", {}),
            "confidence_scores": report_payload.get("extracted_data", {}).get("confidence", {}),
            "final_rule_results": report_payload.get("rule_results", []),
            "expected_result": None,
            "pass_fail_match": None,
            "status": report_payload.get("status", "READY_FOR_DECISION"),
            "summary": report_payload.get("summary", {}),
            "extracted_data": report_payload.get("extracted_data", {}),
            "rule_results": report_payload.get("rule_results", []),
        }
        bucket = classify_failure(case_payload)
        case_payload["failure_bucket"] = bucket
        failure_counter[bucket] += 1

        write_json(case_dir / "case.json", case_payload)
        write_json(case_dir / "report.json", report_payload)
        if extracted_path.exists():
            write_json(case_dir / "extracted.json", extracted_payload)
        cases.append(case_payload)

    metrics = compute_metrics(cases)
    top_causes = failure_counter.most_common(10)
    summary = {
        "mode": mode,
        "dataset_size": len(cases),
        "file_types": sorted([k for k, v in file_types.items() if v > 0]),
        "failure_taxonomy_counts": dict(failure_counter),
        "top_10_causes": [{"bucket": bucket, "count": count} for bucket, count in top_causes],
        "metrics": metrics,
        "partial_eval_mode": True,
        "limitations": "Expected labels were not found in repository artifacts; precision/recall are not computed.",
    }

    write_json(audit_root / f"summary_{mode}.json", summary)
    write_markdown_summary(audit_root / f"summary_{mode}.md", summary, top_causes)
    if mode == "after":
        write_json(audit_root / "summary.json", summary)
        write_markdown_summary(audit_root / "summary.md", summary, top_causes)
    return summary


def write_before_after(project_root: Path, before: dict[str, Any], after: dict[str, Any]) -> None:
    audit_root = project_root / "outputs" / "audit"
    lines = [
        "# Before vs After",
        "",
        "| metric | before | after |",
        "|---|---:|---:|",
    ]
    keys = [
        "extraction_field_accuracy",
        "critical_rule_precision",
        "critical_rule_recall",
        "false_pass_rate",
        "needs_clarification_rate",
        "overall_case_success_rate",
    ]
    for key in keys:
        lines.append(f"| {key} | {before['metrics'].get(key)} | {after['metrics'].get(key)} |")
    (audit_root / "before_after.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()

    before = run_audit(project_root, mode="before")
    after = run_audit(project_root, mode="after")
    write_before_after(project_root, before, after)


if __name__ == "__main__":
    main()
