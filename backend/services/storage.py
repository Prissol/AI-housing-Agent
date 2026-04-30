import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from core.config import get_settings


def ensure_output_dirs() -> None:
    settings = get_settings()
    settings.outputs_root.mkdir(parents=True, exist_ok=True)
    settings.preprocessed_dir.mkdir(parents=True, exist_ok=True)
    settings.extracted_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)


async def save_upload_temp(file: UploadFile, analysis_id: str) -> Path:
    ensure_output_dirs()
    suffix = Path(file.filename or "upload.bin").suffix
    safe_name = f"{analysis_id}_{uuid4().hex}{suffix}"
    target = get_settings().preprocessed_dir / safe_name
    content = await file.read()
    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(f"Upload exceeds max size {settings.max_upload_size_mb}MB.")
    target.write_bytes(content)
    return target


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
