from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_markdown_summary(path: Path, summary: dict[str, Any], top_causes: list[tuple[str, int]]) -> None:
    lines = [
        "# Audit Summary",
        "",
        f"- Dataset size: {summary.get('dataset_size', 0)}",
        f"- File types: {', '.join(summary.get('file_types', [])) or 'n/a'}",
        f"- Labeled eval: {summary.get('metrics', {}).get('labeled_eval')}",
        "",
        "## Top Failure Causes",
    ]
    for idx, (bucket, count) in enumerate(top_causes[:10], start=1):
        lines.append(f"{idx}. {bucket}: {count}")
    lines.extend(
        [
            "",
            "## Metrics",
            f"- extraction_field_accuracy: {summary.get('metrics', {}).get('extraction_field_accuracy')}",
            f"- critical_rule_precision: {summary.get('metrics', {}).get('critical_rule_precision')}",
            f"- critical_rule_recall: {summary.get('metrics', {}).get('critical_rule_recall')}",
            f"- false_pass_rate: {summary.get('metrics', {}).get('false_pass_rate')}",
            f"- needs_clarification_rate: {summary.get('metrics', {}).get('needs_clarification_rate')}",
            f"- overall_case_success_rate: {summary.get('metrics', {}).get('overall_case_success_rate')}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
