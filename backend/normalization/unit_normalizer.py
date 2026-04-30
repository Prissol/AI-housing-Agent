from __future__ import annotations

import re
from typing import Any


UNIT_FACTORS_TO_FT = {
    "ft": 1.0,
    "feet": 1.0,
    "foot": 1.0,
    "in": 1 / 12,
    "inch": 1 / 12,
    "inches": 1 / 12,
    "mm": 0.00328084,
    "cm": 0.0328084,
    "m": 3.28084,
}


def parse_dimension_to_feet(value: Any, unit_hint: str | None = None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace(",", "")
    if not text:
        return None

    # 3'-6" or 3' 6"
    feet_inches = re.search(r"(\d+(?:\.\d+)?)\s*'\s*[- ]?\s*(\d+(?:\.\d+)?)\s*\"", text)
    if feet_inches:
        feet = float(feet_inches.group(1))
        inches = float(feet_inches.group(2))
        return feet + (inches / 12.0)

    # 3ft 6in
    ft_in = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|feet|foot)\s*(\d+(?:\.\d+)?)\s*(?:in|inch|inches)", text)
    if ft_in:
        return float(ft_in.group(1)) + float(ft_in.group(2)) / 12.0

    num_match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not num_match:
        return None
    num = float(num_match.group(1))

    combined = f"{text} {unit_hint or ''}".lower()
    for unit, factor in UNIT_FACTORS_TO_FT.items():
        if re.search(rf"\b{re.escape(unit)}\b", combined):
            return num * factor
    return num
