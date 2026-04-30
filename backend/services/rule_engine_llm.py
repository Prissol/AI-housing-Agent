from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq

from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _extract_numeric_constraint(rule: str, field: str) -> tuple[str, float] | None:
    if field not in rule.lower():
        return None
    if "<=" in rule:
        sign = "<="
    elif ">=" in rule:
        sign = ">="
    else:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", rule)
    if not match:
        return None
    return sign, float(match.group(1))


def _strict_missing_measurement_violations(rules: list[str], features: dict[str, Any]) -> list[str]:
    strict_violations: list[str] = []
    for rule in rules:
        lower_rule = rule.lower()
        if "height" in lower_rule and _extract_numeric_constraint(rule, "height"):
            if features.get("building_height_ft") is None:
                strict_violations.append("Building height could not be verified from detection output")
        if "road width" in lower_rule and _extract_numeric_constraint(rule, "road width"):
            if features.get("road_width_ft") is None:
                strict_violations.append("Road width could not be verified from detection output")
    return strict_violations


def _fallback_evaluate(rules: list[str], features: dict[str, Any], detections: list[dict[str, Any]]) -> dict:
    violations: list[str] = []
    detection_labels = {d.get("label", "").lower() for d in detections}

    for rule in rules:
        lower_rule = rule.lower()
        height = features.get("building_height_ft")
        width = features.get("road_width_ft")

        constraint = _extract_numeric_constraint(rule, "height")
        if constraint:
            sign, limit = constraint
            if height is None:
                violations.append(f"Building height could not be verified against limit {limit} ft")
            elif sign == "<=" and height > limit:
                violations.append(f"Building height exceeds {limit} ft")
            elif sign == ">=" and height < limit:
                violations.append(f"Building height below required {limit} ft")

        constraint = _extract_numeric_constraint(rule, "road width")
        if constraint:
            sign, limit = constraint
            if width is None:
                violations.append(f"Road width could not be verified against limit {limit} ft")
            elif sign == "<=" and width > limit:
                violations.append(f"Road width exceeds allowed {limit} ft")
            elif sign == ">=" and width < limit:
                violations.append(f"Road width is less than {limit} ft")

        if "no commercial" in lower_rule and "commercial" in detection_labels:
            violations.append("Commercial building detected in restricted zone")

    status = "REJECT" if violations else "ACCEPT"
    explanation = (
        "Image violates one or more bylaws."
        if violations
        else "No clear bylaw violation was detected from available features."
    )
    return {"status": status, "violations": violations, "explanation": explanation}


def _parse_llm_json(content: str) -> dict | None:
    try:
        return json.loads(content)
    except Exception:
        pass

    match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def evaluate_with_llm_or_fallback(
    rules: list[str],
    features: dict[str, Any],
    detections: list[dict[str, Any]],
) -> dict:
    if not settings.groq_api_key:
        fallback = _fallback_evaluate(rules, features, detections)
        extra = _strict_missing_measurement_violations(rules, features)
        violations = [*fallback.get("violations", []), *extra]
        deduped = list(dict.fromkeys([str(v) for v in violations]))
        status = "REJECT" if deduped else "ACCEPT"
        return {
            "status": status,
            "violations": deduped,
            "explanation": fallback.get("explanation", ""),
        }

    prompt = {
        "rules": rules,
        "features": features,
        "detections": detections,
        "instruction": (
            "Return STRICT JSON only with keys: status, violations, explanation. "
            "status must be ACCEPT or REJECT. If any violation exists, REJECT."
        ),
    }
    system = (
        "You are a strict architecture bylaw validation engine. "
        "No markdown, no prose outside JSON."
    )

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0,
            max_completion_tokens=500,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(prompt)},
            ],
        )
        content = (response.choices[0].message.content or "").strip()
        parsed = _parse_llm_json(content)
        if not parsed:
            raise ValueError("Could not parse LLM JSON response")
        status = str(parsed.get("status", "REJECT")).upper()
        violations = parsed.get("violations", []) or []
        explanation = str(parsed.get("explanation", ""))
        if status not in {"ACCEPT", "REJECT"}:
            status = "REJECT"
        if status == "ACCEPT" and violations:
            status = "REJECT"
        llm_result = {
            "status": status,
            "violations": [str(v) for v in violations],
            "explanation": explanation,
        }
        extra = _strict_missing_measurement_violations(rules, features)
        if extra:
            merged = list(dict.fromkeys([*llm_result["violations"], *extra]))
            llm_result["violations"] = merged
            llm_result["status"] = "REJECT"
            if not llm_result["explanation"]:
                llm_result["explanation"] = "Required bylaw measurements could not be verified."
        return llm_result
    except Exception as exc:
        logger.warning("LLM rule evaluation failed, using fallback: %s", exc)
        return _fallback_evaluate(rules, features, detections)
