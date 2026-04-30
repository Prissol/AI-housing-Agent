import re

from schemas.analyze import Finding, Severity

RESIDENTIAL_SETBACK_RULES: dict[str, dict[str, float]] = {
    "5 marla": {"front": 5, "rear": 2.5, "side": 0},
    "8 marla": {"front": 5, "rear": 3, "side": 3},
    "10 marla": {"front": 5, "rear": 3, "side": 5},
    "12 marla": {"front": 5, "rear": 3, "side": 5},
    "1 kanal": {"front": 15, "rear": 5, "side": 5},
    "2 kanal": {"front": 20, "rear": 8, "side": 5},
    "4 kanal": {"front": 30, "rear": 10, "side": 15},
}


def _normalize_text(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("`", "'")
        .replace("’", "'")
        .replace("“", "")
        .replace("”", "")
    )


def _detect_plot_type(text: str) -> str | None:
    for plot_type in RESIDENTIAL_SETBACK_RULES:
        if plot_type in text:
            return plot_type
    return None


def _read_feet_value_after_keyword(text: str, keyword: str) -> float | None:
    pattern = re.compile(
        rf"{keyword}\s*(?:setback|open\s*space|cos)?\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|')",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_building_height(text: str) -> float | None:
    pattern = re.compile(
        r"(?:overall|building)?\s*height\s*[:=-]?\s*(\d+(?:\.\d+)?)\s*(?:ft|feet|')",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_floor_count(text: str) -> int | None:
    if re.search(r"\bb\+g\+2\b|\bg\+2\b|\bground\+2\b", text, flags=re.IGNORECASE):
        return 3
    if re.search(r"\bb\+g\+1\b|\bg\+1\b|\bground\+1\b", text, flags=re.IGNORECASE):
        return 2

    story_match = re.search(r"(\d+)\s*stor(?:e)?y", text, flags=re.IGNORECASE)
    if not story_match:
        return None
    try:
        return int(story_match.group(1))
    except ValueError:
        return None


def evaluate_bylaw_signals(
    ocr_text: str,
    enforce_bylaw_evidence: bool = True,
) -> dict:
    normalized = _normalize_text(ocr_text)
    findings: list[Finding] = []
    notes: list[str] = []
    risk_delta = 0.0
    violation_detected = False
    rule_checks: list[dict] = []

    def add_rule_check(rule: str, observed: str, passed: bool, reason: str) -> None:
        rule_checks.append(
            {
                "rule": rule,
                "observed": observed,
                "passed": passed,
                "reason": reason,
            }
        )

    if "duplex" in normalized:
        findings.append(
            Finding(
                code="DUPLEX_NOT_ALLOWED",
                title="Duplex construction detected",
                description="DHA by-laws mark duplex design as non-compliant in this rule set.",
                severity=Severity.HIGH,
            )
        )
        risk_delta += 0.45
        violation_detected = True
        add_rule_check(
            rule="Duplex construction is not permitted.",
            observed="Duplex keyword detected in OCR text.",
            passed=False,
            reason="Plan indicates duplex usage, which is not allowed in this rule set.",
        )
    else:
        add_rule_check(
            rule="Duplex construction is not permitted.",
            observed="No duplex marker found in OCR text.",
            passed=True,
            reason="No duplex-specific evidence detected.",
        )

    height_ft = _extract_building_height(normalized)
    if height_ft is not None and height_ft > 40:
        findings.append(
            Finding(
                code="HEIGHT_LIMIT_EXCEEDED",
                title="Building height above limit",
                description=f"Building height ({height_ft} ft) exceeds maximum allowed 40 ft.",
                severity=Severity.HIGH,
            )
        )
        risk_delta += 0.45
        violation_detected = True
        add_rule_check(
            rule="Building height must be <= 40 ft.",
            observed=f"Building height detected: {height_ft} ft.",
            passed=False,
            reason="Detected height exceeds the 40 ft limit.",
        )
    elif height_ft is not None:
        add_rule_check(
            rule="Building height must be <= 40 ft.",
            observed=f"Building height detected: {height_ft} ft.",
            passed=True,
            reason="Detected height is within the 40 ft limit.",
        )
    else:
        add_rule_check(
            rule="Building height must be <= 40 ft.",
            observed="No measurable height value found.",
            passed=not enforce_bylaw_evidence,
            reason=(
                "Height value is missing; strict mode treats this as non-compliant."
                if enforce_bylaw_evidence
                else "Height value is missing; rule marked as review-needed."
            ),
        )

    floor_count = _extract_floor_count(normalized)
    if floor_count is not None and floor_count > 2:
        findings.append(
            Finding(
                code="FLOOR_LIMIT_EXCEEDED",
                title="Storey count above limit",
                description="Detected storey count appears above allowed B+G+1 limit.",
                severity=Severity.HIGH,
            )
        )
        risk_delta += 0.4
        violation_detected = True
        add_rule_check(
            rule="Storey count must not exceed B+G+1 (2 storeys above ground context).",
            observed=f"Storey count detected: {floor_count}.",
            passed=False,
            reason="Detected floor count exceeds allowed limit.",
        )
    elif floor_count is not None:
        add_rule_check(
            rule="Storey count must not exceed B+G+1 (2 storeys above ground context).",
            observed=f"Storey count detected: {floor_count}.",
            passed=True,
            reason="Detected floor count is within allowed limit.",
        )
    else:
        add_rule_check(
            rule="Storey count must not exceed B+G+1 (2 storeys above ground context).",
            observed="No reliable floor-count marker detected.",
            passed=not enforce_bylaw_evidence,
            reason=(
                "Floor count is missing; strict mode treats this as non-compliant."
                if enforce_bylaw_evidence
                else "Floor count is missing; rule marked as review-needed."
            ),
        )

    plot_type = _detect_plot_type(normalized)
    if plot_type:
        required = RESIDENTIAL_SETBACK_RULES[plot_type]
        front = _read_feet_value_after_keyword(normalized, "front")
        rear = _read_feet_value_after_keyword(normalized, "rear")
        side = _read_feet_value_after_keyword(normalized, "side")
        notes.append(
            (
                f"Plot type detected: {plot_type}; expected setbacks "
                f"front {required['front']} ft, rear {required['rear']} ft, side {required['side']} ft."
            )
        )

        if front is not None and front < required["front"]:
            findings.append(
                Finding(
                    code="FRONT_SETBACK_VIOLATION",
                    title="Front setback below minimum",
                    description=(
                        f"Front setback ({front} ft) is below required "
                        f"{required['front']} ft for {plot_type}."
                    ),
                    severity=Severity.HIGH,
                )
            )
            risk_delta += 0.35
            violation_detected = True
        if rear is not None and rear < required["rear"]:
            findings.append(
                Finding(
                    code="REAR_SETBACK_VIOLATION",
                    title="Rear setback below minimum",
                    description=(
                        f"Rear setback ({rear} ft) is below required "
                        f"{required['rear']} ft for {plot_type}."
                    ),
                    severity=Severity.HIGH,
                )
            )
            risk_delta += 0.35
            violation_detected = True
        if required["side"] > 0 and side is not None and side < required["side"]:
            findings.append(
                Finding(
                    code="SIDE_SETBACK_VIOLATION",
                    title="Side setback below minimum",
                    description=(
                        f"Side setback ({side} ft) is below required "
                        f"{required['side']} ft for {plot_type}."
                    ),
                    severity=Severity.HIGH,
                )
            )
            risk_delta += 0.35
            violation_detected = True
        setback_issues: list[str] = []
        if front is None:
            setback_issues.append("front setback missing")
        elif front < required["front"]:
            setback_issues.append(f"front {front} ft < required {required['front']} ft")
        if rear is None:
            setback_issues.append("rear setback missing")
        elif rear < required["rear"]:
            setback_issues.append(f"rear {rear} ft < required {required['rear']} ft")
        if required["side"] > 0:
            if side is None:
                setback_issues.append("side setback missing")
            elif side < required["side"]:
                setback_issues.append(f"side {side} ft < required {required['side']} ft")

        if setback_issues:
            add_rule_check(
                rule="Setback requirements must satisfy plot-type minimums.",
                observed=(
                    f"Plot type: {plot_type}. "
                    f"Readings -> front: {front}, rear: {rear}, side: {side}."
                ),
                passed=False if enforce_bylaw_evidence else len(setback_issues) == 0,
                reason="; ".join(setback_issues),
            )
            if enforce_bylaw_evidence:
                violation_detected = True
                risk_delta += 0.2
        else:
            add_rule_check(
                rule="Setback requirements must satisfy plot-type minimums.",
                observed=(
                    f"Plot type: {plot_type}. "
                    f"Readings -> front: {front}, rear: {rear}, side: {side}."
                ),
                passed=True,
                reason="All detected setback values satisfy required minimums.",
            )
    else:
        notes.append("Plot type not clearly detected from OCR text.")
        add_rule_check(
            rule="Setback requirements must satisfy plot-type minimums.",
            observed="Plot type could not be detected from OCR text.",
            passed=not enforce_bylaw_evidence,
            reason=(
                "Plot type is required to validate setbacks in strict mode."
                if enforce_bylaw_evidence
                else "Plot type missing; setback validation deferred."
            ),
        )

    has_core_evidence = any(
        [
            plot_type is not None,
            _read_feet_value_after_keyword(normalized, "front") is not None,
            _read_feet_value_after_keyword(normalized, "rear") is not None,
            _read_feet_value_after_keyword(normalized, "side") is not None,
            height_ft is not None,
            floor_count is not None,
        ]
    )

    if enforce_bylaw_evidence and not has_core_evidence:
        findings.append(
            Finding(
                code="INSUFFICIENT_BYLAW_EVIDENCE",
                title="Insufficient measurable bylaw evidence",
                description=(
                    "OCR text does not clearly provide plot type, setbacks, height, or floors. "
                    "Manual review required."
                ),
                severity=Severity.HIGH,
            )
        )
        risk_delta += 0.45
        violation_detected = True
        add_rule_check(
            rule="Core bylaw evidence must be present (plot type, setbacks, height, or floors).",
            observed="Core measurable bylaw evidence not found.",
            passed=False,
            reason="Strict mode requires measurable bylaw evidence for compliance decision.",
        )
    elif has_core_evidence:
        add_rule_check(
            rule="Core bylaw evidence must be present (plot type, setbacks, height, or floors).",
            observed="Measurable bylaw evidence was detected.",
            passed=True,
            reason="Evidence is sufficient for bylaw evaluation.",
        )

    return {
        "risk_delta": min(max(risk_delta, 0.0), 1.0),
        "findings": findings,
        "notes": notes,
        "violation_detected": violation_detected,
        "has_core_evidence": has_core_evidence,
        "rule_checks": rule_checks,
    }
