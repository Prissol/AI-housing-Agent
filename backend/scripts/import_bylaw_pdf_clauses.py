from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.mongo import bylaw_clauses_collection, bylaw_sets_collection, utcnow
from rules.bylaw_repository import get_bylaw_profile_payload


def _read_pdf_text(path: Path) -> str:
    text_parts: list[str] = []
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
    except Exception:
        text_parts = []
    text = "\n".join(text_parts).strip()
    if text:
        return text

    try:
        import fitz  # type: ignore

        doc = fitz.open(str(path))
        parts = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _extract_threshold(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                continue
    return None


def _extract_feet_from_line(patterns: list[str], text: str) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            value = float(match.group(1))
            if value > 0:
                return value
        except Exception:
            continue
    return None


def _parse_clauses_from_text(text: str) -> list[dict]:
    normalized = re.sub(r"\s+", " ", text)
    clauses: list[dict] = []

    stair = _extract_threshold(
        [
            r"(?:minimum|min)\s+stair(?:case)?\s+(?:clear\s+)?width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
            r"stair(?:case)?\s+width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
        ],
        normalized,
    )
    if stair is not None:
        clauses.append(
            {
                "clause_id": "STAIR_MIN_WIDTH",
                "text": "Minimum stair clear width",
                "field_path": "stairs.width_ft",
                "operator": ">=",
                "threshold": stair,
                "unit": "ft",
                "severity": "high",
            }
        )

    exit_w = _extract_threshold(
        [
            r"(?:minimum|min)\s+exit\s+(?:clear\s+)?width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
            r"exit\s+width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
        ],
        normalized,
    )
    if exit_w is not None:
        clauses.append(
            {
                "clause_id": "EXIT_MIN_WIDTH",
                "text": "Minimum exit clear width",
                "field_path": "exits.width_ft",
                "operator": ">=",
                "threshold": exit_w,
                "unit": "ft",
                "severity": "high",
            }
        )

    corridor = _extract_threshold(
        [
            r"(?:minimum|min)\s+corridor\s+(?:clear\s+)?width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
            r"corridor\s+width[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:ft|feet)",
        ],
        normalized,
    )
    if corridor is not None:
        clauses.append(
            {
                "clause_id": "CORRIDOR_MIN_WIDTH",
                "text": "Minimum corridor clear width",
                "field_path": "corridors.width_ft",
                "operator": ">=",
                "threshold": corridor,
                "unit": "ft",
                "severity": "medium",
            }
        )

    room_area = _extract_threshold(
        [
            r"(?:minimum|min)\s+room\s+area[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",
            r"room\s+area[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)\s*(?:sq\.?\s*ft|sqft|square\s*feet)",
        ],
        normalized,
    )
    if room_area is not None:
        clauses.append(
            {
                "clause_id": "ROOM_MIN_AREA",
                "text": "Minimum room area",
                "field_path": "rooms.area_sqft",
                "operator": ">=",
                "threshold": room_area,
                "unit": "sqft",
                "severity": "medium",
            }
        )

    max_floors = _extract_threshold(
        [
            r"max(?:imum)?\s+floors?\s+without\s+lift[^0-9]{0,20}([0-9]+)",
            r"without\s+lift[^0-9]{0,20}up\s*to[^0-9]{0,20}([0-9]+)\s+floors?",
        ],
        normalized,
    )
    if max_floors is not None:
        clauses.append(
            {
                "clause_id": "MAX_FLOORS_WITHOUT_LIFT",
                "text": "Maximum floors allowed without lift",
                "field_path": "floors.count",
                "operator": "<=",
                "threshold": max_floors,
                "unit": "count",
                "severity": "high",
            }
        )
    else:
        floor_expr = re.search(r"floors?\s+allowed[^A-Za-z0-9]{0,15}\(([A-Za-z0-9+\s]+)\)", normalized, flags=re.IGNORECASE)
        if floor_expr:
            tokens = [token.strip() for token in floor_expr.group(1).split("+") if token.strip()]
            derived_count = float(len(tokens)) if tokens else None
            if derived_count:
                clauses.append(
                    {
                        "clause_id": "MAX_ALLOWED_FLOORS",
                        "text": f"Maximum allowed floors expression: {floor_expr.group(1).strip()}",
                        "field_path": "floors.count",
                        "operator": "<=",
                        "threshold": derived_count,
                        "unit": "count",
                        "severity": "high",
                    }
                )

    max_height = _extract_threshold(
        [
            r"max\.?\s*height[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
            r"maximum\s+height[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
        ],
        normalized,
    )
    if max_height is not None:
        clauses.append(
            {
                "clause_id": "MAX_BUILDING_HEIGHT",
                "text": "Maximum building height",
                "field_path": "dimensions.height_ft_max",
                "operator": "<=",
                "threshold": max_height,
                "unit": "ft",
                "severity": "high",
            }
        )

    front_setback = _extract_threshold(
        [
            r"front\s+cos[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
            r"front\s+setback[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
        ],
        normalized,
    )
    if front_setback is None:
        front_setback = _extract_feet_from_line(
            [
                r"front\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
                r"front\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[-][0-9]+",
                r"front\s+setback[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
            ],
            normalized,
        )
    if front_setback is not None:
        clauses.append(
            {
                "clause_id": "FRONT_SETBACK_MIN",
                "text": "Minimum front setback",
                "field_path": "dimensions.front_setback_ft_min",
                "operator": ">=",
                "threshold": front_setback,
                "unit": "ft",
                "severity": "medium",
            }
        )

    rear_setback = _extract_threshold(
        [
            r"rear\s+cos[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
            r"rear\s+setback[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
        ],
        normalized,
    )
    if rear_setback is None:
        rear_setback = _extract_feet_from_line(
            [
                r"rear\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
                r"rear\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[-][0-9]+",
                r"rear\s+setback[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
            ],
            normalized,
        )
    if rear_setback is not None:
        clauses.append(
            {
                "clause_id": "REAR_SETBACK_MIN",
                "text": "Minimum rear setback",
                "field_path": "dimensions.rear_setback_ft_min",
                "operator": ">=",
                "threshold": rear_setback,
                "unit": "ft",
                "severity": "medium",
            }
        )

    side_setback = _extract_threshold(
        [
            r"side(?:s)?\s+cos[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
            r"side(?:s)?\s+setback[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
        ],
        normalized,
    )
    if side_setback is None:
        side_setback = _extract_feet_from_line(
            [
                r"side(?:s)?\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
                r"side(?:s)?\s+cos[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[-][0-9]+",
                r"side(?:s)?\s+setback[^0-9]{0,25}([0-9]+(?:\.[0-9]+)?)\s*[\'`′’]",
            ],
            normalized,
        )
    if side_setback is not None:
        clauses.append(
            {
                "clause_id": "SIDE_SETBACK_MIN",
                "text": "Minimum side setback",
                "field_path": "dimensions.side_setback_ft_min",
                "operator": ">=",
                "threshold": side_setback,
                "unit": "ft",
                "severity": "medium",
            }
        )

    return clauses


def _is_in_range(clause_id: str, value: float) -> bool:
    ranges = {
        "STAIR_MIN_WIDTH": (2, 20),
        "EXIT_MIN_WIDTH": (2, 20),
        "CORRIDOR_MIN_WIDTH": (2, 30),
        "ROOM_MIN_AREA": (20, 5000),
        "MAX_FLOORS_WITHOUT_LIFT": (1, 20),
        "MAX_ALLOWED_FLOORS": (1, 20),
        "MAX_BUILDING_HEIGHT": (8, 300),
        "FRONT_SETBACK_MIN": (2, 35),
        "REAR_SETBACK_MIN": (2, 25),
        "SIDE_SETBACK_MIN": (2, 25),
    }
    low, high = ranges.get(clause_id, (-1e9, 1e9))
    return low <= value <= high


def _baseline_clauses_from_profile(profile_id: str) -> list[dict]:
    profile = get_bylaw_profile_payload(profile_id)
    return [
        {
            "clause_id": "STAIR_MIN_WIDTH",
            "text": "Minimum stair clear width",
            "field_path": "stairs.width_ft",
            "operator": ">=",
            "threshold": float(profile.get("min_stair_width_ft", 4.0)),
            "unit": "ft",
            "severity": "high",
            "evaluation_mode": "deterministic",
        },
        {
            "clause_id": "EXIT_MIN_WIDTH",
            "text": "Minimum exit clear width",
            "field_path": "exits.width_ft",
            "operator": ">=",
            "threshold": float(profile.get("min_exit_width_ft", 4.0)),
            "unit": "ft",
            "severity": "high",
            "evaluation_mode": "deterministic",
        },
        {
            "clause_id": "CORRIDOR_MIN_WIDTH",
            "text": "Minimum corridor clear width",
            "field_path": "corridors.width_ft",
            "operator": ">=",
            "threshold": float(profile.get("min_corridor_width_ft", 5.0)),
            "unit": "ft",
            "severity": "medium",
            "evaluation_mode": "deterministic",
        },
        {
            "clause_id": "ROOM_MIN_AREA",
            "text": "Minimum room area",
            "field_path": "rooms.area_sqft",
            "operator": ">=",
            "threshold": float(profile.get("min_room_area_sqft", 80.0)),
            "unit": "sqft",
            "severity": "medium",
            "evaluation_mode": "deterministic",
        },
        {
            "clause_id": "MAX_FLOORS_WITHOUT_LIFT",
            "text": "Maximum floors allowed without lift",
            "field_path": "floors.count_without_lift",
            "operator": "<=",
            "threshold": float(profile.get("max_floors_without_lift", 3)),
            "unit": "count",
            "severity": "high",
            "evaluation_mode": "deterministic",
        },
    ]


def _manual_reference_clauses(text: str, profile_id: str) -> list[dict]:
    # Keep broad bylaw coverage in DB, even when a clause is not auto-measurable yet.
    raw_lines = [line.strip() for line in text.splitlines() if line and len(line.strip()) > 18]
    filtered: list[str] = []
    keywords = (
        "must",
        "shall",
        "required",
        "not allowed",
        "allowed",
        "minimum",
        "maximum",
        "height",
        "setback",
        "cos",
        "parking",
        "road",
        "coverage",
        "far",
        "boundary wall",
        "lift",
    )
    for line in raw_lines:
        normalized = re.sub(r"\s+", " ", line)
        lower = normalized.lower()
        if any(token in lower for token in keywords):
            filtered.append(normalized)
    deduped: list[str] = []
    seen: set[str] = set()
    for line in filtered:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    manual_clauses: list[dict] = []
    for idx, clause_text in enumerate(deduped[:220], start=1):
        manual_clauses.append(
            {
                "clause_id": f"{profile_id.upper()}_REF_{idx:03d}",
                "text": clause_text,
                "field_path": "",
                "operator": "manual",
                "threshold": None,
                "unit": "",
                "severity": "info",
                "evaluation_mode": "manual",
            }
        )
    return manual_clauses


def import_bylaw_pdf(profile_id: str, pdf_path: Path, version: str = "2025.1") -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    text = _read_pdf_text(pdf_path)
    if not text:
        raise RuntimeError("Unable to read text from PDF.")

    parsed = _parse_clauses_from_text(text)
    for item in parsed:
        item.setdefault("evaluation_mode", "deterministic")
    baseline = _baseline_clauses_from_profile(profile_id)
    merged: dict[str, dict] = {item["clause_id"]: item for item in baseline}
    for item in parsed:
        threshold = float(item.get("threshold", 0))
        if _is_in_range(item["clause_id"], threshold):
            merged[item["clause_id"]] = item
    deterministic_clauses = list(merged.values())
    manual_clauses = _manual_reference_clauses(text, profile_id)
    clauses = deterministic_clauses + manual_clauses
    if not deterministic_clauses:
        raise RuntimeError("No usable clauses prepared for import.")

    now = utcnow()
    set_doc = bylaw_sets_collection().find_one({"name": profile_id, "version": version})
    if not set_doc:
        set_id = bylaw_sets_collection().insert_one(
            {"name": profile_id, "version": version, "city": "Multan", "status": "active", "created_at": now}
        ).inserted_id
        set_id_str = str(set_id)
    else:
        set_id_str = str(set_doc["_id"])

    bylaw_clauses_collection().delete_many({"bylaw_set_id": set_id_str})
    payload = [{**clause, "bylaw_set_id": set_id_str, "source_file": str(pdf_path), "created_at": now} for clause in clauses]
    bylaw_clauses_collection().insert_many(payload)
    print(
        f"Imported {len(payload)} clauses for profile '{profile_id}' from {pdf_path.name}. "
        f"(deterministic={len(deterministic_clauses)}, manual_reference={len(manual_clauses)})"
    )


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/import_bylaw_pdf_clauses.py <profile_id> <pdf_path> [version]")
        raise SystemExit(1)
    profile = sys.argv[1].strip()
    pdf = Path(sys.argv[2]).expanduser()
    ver = sys.argv[3].strip() if len(sys.argv) > 3 else "2025.1"
    import_bylaw_pdf(profile, pdf, ver)
