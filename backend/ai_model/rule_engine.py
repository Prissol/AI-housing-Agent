from ai_model.feature_extractor import MapFeatures
from schemas.analyze import ComplianceStatus, Finding, Severity


def evaluate_map_rules(features: MapFeatures) -> dict:
    findings: list[Finding] = []
    risk_score = 0.0

    if features.width < 500 or features.height < 500:
        findings.append(
            Finding(
                code="LOW_RESOLUTION",
                title="Low image resolution",
                description="Image resolution is too small for reliable bylaw assessment.",
                severity=Severity.HIGH,
            )
        )
        risk_score += 0.35

    if features.contrast_score < 28:
        findings.append(
            Finding(
                code="LOW_CONTRAST",
                title="Low contrast plan",
                description="Map lines are not well separated from the background.",
                severity=Severity.MEDIUM,
            )
        )
        risk_score += 0.15

    if features.sharpness_score < 75:
        findings.append(
            Finding(
                code="BLURRY_IMAGE",
                title="Blurry drawing",
                description="Blurry input can hide setbacks, labels, or wall boundaries.",
                severity=Severity.HIGH,
            )
        )
        risk_score += 0.25

    if features.line_count < 40:
        findings.append(
            Finding(
                code="INSUFFICIENT_LAYOUT_LINES",
                title="Insufficient layout detail",
                description="Detected line geometry is too low for a typical housing plan.",
                severity=Severity.HIGH,
            )
        )
        risk_score += 0.25

    if features.edge_density < 0.015:
        findings.append(
            Finding(
                code="SPARSE_DRAWING",
                title="Sparse structural content",
                description="Map appears too empty; required architectural detail may be missing.",
                severity=Severity.MEDIUM,
            )
        )
        risk_score += 0.12
    elif features.edge_density > 0.23:
        findings.append(
            Finding(
                code="OVER_DENSE_DRAWING",
                title="Overly dense drawing",
                description="Drawing density is unusually high and may indicate cluttered or overlapping plan data.",
                severity=Severity.MEDIUM,
            )
        )
        risk_score += 0.12

    if features.rectangle_count < 3:
        findings.append(
            Finding(
                code="FEW_ENCLOSED_SPACES",
                title="Few enclosed spaces detected",
                description="The plan has too few enclosed rectangular sections for room-level analysis.",
                severity=Severity.MEDIUM,
            )
        )
        risk_score += 0.1

    if features.foreground_ratio > 0.52:
        findings.append(
            Finding(
                code="EXCESSIVE_FILLED_AREA",
                title="Excessive filled area",
                description="Too much foreground ink may hide key bylaw-relevant boundaries.",
                severity=Severity.LOW,
            )
        )
        risk_score += 0.08

    risk_score = min(max(risk_score, 0.0), 1.0)
    confidence = max(0.0, min(1.0, 0.95 - (risk_score * 0.7)))
    is_violation = risk_score >= 0.35

    if is_violation:
        details = (
            "Potential compliance risks were detected from plan-quality and structural indicators. "
            "Please review the listed findings before approval."
        )
        status = ComplianceStatus.VIOLATION
    else:
        details = (
            "No material visual compliance risk was detected. "
            "Plan quality is sufficient for preliminary compliance review."
        )
        status = ComplianceStatus.NO_VIOLATION

    return {
        "status": status,
        "details": details,
        "confidence": round(confidence, 3),
        "risk_score": round(risk_score, 3),
        "findings": findings,
    }
