from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import get_settings


def _state_path(analysis_id: str) -> Path:
    settings = get_settings()
    return settings.reports_dir / f"{analysis_id}.clarifications.json"


def save_clarification_state(analysis_id: str, payload: dict[str, Any]) -> None:
    path = _state_path(analysis_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_clarification_state(analysis_id: str) -> dict[str, Any] | None:
    path = _state_path(analysis_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def merge_answers(existing: dict[str, Any] | None, answers: list[dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    if existing:
        merged.update(existing)
    for item in answers:
        qid = str(item.get("question_id", "")).strip()
        ans = str(item.get("answer", "")).strip()
        if qid and ans:
            merged[qid] = ans
    return merged
