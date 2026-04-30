import cv2
import numpy as np
from fastapi import HTTPException, status

from ai_model.bylaw_rules import evaluate_bylaw_signals
from ai_model.feature_extractor import extract_map_features
from ai_model.ocr_extractor import extract_ocr_text
from ai_model.rule_engine import evaluate_map_rules
from schemas.analyze import AnalysisMetrics, AnalyzeMapResponse, ComplianceStatus, Finding, Severity
from utils.config import settings
from utils.logger import get_logger
from utils.validators import MIN_HEIGHT, MIN_WIDTH

logger = get_logger(__name__)


def _format_bylaw_rule_checks(rule_checks: list[dict]) -> str:
    formatted: list[str] = []
    for idx, item in enumerate(rule_checks, start=1):
        verdict = "PASS" if item.get("passed") else "FAIL"
        rule = str(item.get("rule", "")).strip()
        observed = str(item.get("observed", "")).strip()
        reason = str(item.get("reason", "")).strip()
        formatted.append(f"{idx}) [{verdict}] Rule: {rule} | Observed: {observed} | Reason: {reason}")
    return " ; ".join(formatted)


def _format_rule_title(item: dict) -> str:
    rule = str(item.get("rule", "")).strip().rstrip(".")
    reason = str(item.get("reason", "")).strip().rstrip(".")
    observed = str(item.get("observed", "")).strip().rstrip(".")
    if reason:
        return f"{rule} ({reason})"
    if observed:
        return f"{rule} (Observed: {observed})"
    return rule


def analyze_housing_map(image_bytes: bytes, filename: str) -> AnalyzeMapResponse:
    np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Please upload a valid image.",
        )

    features = extract_map_features(image)

    if features.width < MIN_WIDTH or features.height < MIN_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Image resolution too small. Minimum required size is "
                f"{MIN_WIDTH}x{MIN_HEIGHT}."
            ),
        )

    logger.debug(
        (
            "Image metrics for %s => %sx%s edge_density=%.4f lines=%s rectangles=%s "
            "foreground=%.4f sharpness=%.2f contrast=%.2f"
        ),
        filename,
        features.width,
        features.height,
        features.edge_density,
        features.line_count,
        features.rectangle_count,
        features.foreground_ratio,
        features.sharpness_score,
        features.contrast_score,
    )

    _ = evaluate_map_rules(features)
    findings = []
    risk_score = 0.0
    details_parts = []
    status_value = ComplianceStatus.NO_VIOLATION

    ocr_text, ocr_issue = extract_ocr_text(image)
    bylaw_eval = evaluate_bylaw_signals(
        ocr_text=ocr_text,
        enforce_bylaw_evidence=settings.enforce_bylaw_evidence,
    )
    findings.extend(bylaw_eval["findings"])
    risk_score = min(max(risk_score + bylaw_eval["risk_delta"], 0.0), 1.0)

    rule_checks = bylaw_eval.get("rule_checks", [])
    if rule_checks:
        details_parts.append(f"Rule-wise bylaw validation completed for {len(rule_checks)} checks.")
    elif bylaw_eval["notes"]:
        details_parts.append("Bylaw assessment: " + " ".join(bylaw_eval["notes"]))
    if ocr_issue == "OCR_ENGINE_UNAVAILABLE":
        details_parts.append(
            "OCR engine unavailable on server; strict bylaw evidence mode may trigger manual-review rejection."
        )
    elif ocr_issue == "OCR_BINARY_NOT_FOUND":
        details_parts.append(
            "Tesseract binary is not installed on server; OCR text extraction is unavailable."
        )
    elif ocr_issue == "OCR_TEXT_EMPTY":
        details_parts.append("OCR could not extract sufficiently clear text from this plan image.")
    elif ocr_issue == "OCR_FAILED":
        details_parts.append("OCR extraction failed for this image.")

    if bylaw_eval["violation_detected"]:
        status_value = ComplianceStatus.VIOLATION

    failed_checks = [item for item in rule_checks if not item.get("passed")]
    if failed_checks:
        status_value = ComplianceStatus.VIOLATION
    confidence = max(0.0, min(1.0, 0.95 - (risk_score * 0.7)))

    metrics = AnalysisMetrics(
        width=features.width,
        height=features.height,
        edge_density=round(features.edge_density, 4),
        line_count=features.line_count,
        rectangle_count=features.rectangle_count,
        foreground_ratio=round(features.foreground_ratio, 4),
        sharpness_score=round(features.sharpness_score, 2),
        contrast_score=round(features.contrast_score, 2),
    )

    decision_label = "Non-Compliant" if status_value == ComplianceStatus.VIOLATION else "Compliant"
    passed_checks = [item for item in rule_checks if item.get("passed")]
    violation_lines = [_format_rule_title(item) for item in failed_checks]
    passed_lines = [_format_rule_title(item) for item in passed_checks]

    summary_lines = [f"Compliance Decision: {decision_label}"]
    summary_lines.append("Violations:")
    if violation_lines:
        summary_lines.extend([f"- {line}" for line in violation_lines])
    else:
        summary_lines.append("- None")

    summary_lines.append("Passed Checks:")
    if passed_lines:
        summary_lines.extend([f"- {line}" for line in passed_lines])
    else:
        summary_lines.append("- None")

    summary_lines.append("Observations:")
    if details_parts:
        summary_lines.extend([f"- {line}" for line in details_parts])
    else:
        summary_lines.append("- No additional observations available.")

    details = "\n".join(summary_lines)

    return AnalyzeMapResponse(
        status=status_value,
        details=details,
        confidence=round(confidence, 3),
        risk_score=round(risk_score, 3),
        findings=findings,
        metrics=metrics,
    )
