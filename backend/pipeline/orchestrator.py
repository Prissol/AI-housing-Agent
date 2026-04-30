from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from core.logger import get_logger
from core.config import get_settings
from normalization.unit_normalizer import parse_dimension_to_feet
from pipeline.dwg_ingest import DwgIngestError, cleanup_dwg_temp, ingest_dwg
from pipeline.dwg_normalize import normalize_dwg_payload
from pipeline.dwg_parser import parse_dxf_entities
from pipeline.normalize import normalize_extracted
from policy.decision_gate import REQUIRED_FIELDS, apply_decision_gate
from policy.answer_policy import evaluate_answer_policy
from pipeline.ocr_extract import extract_ocr_blocks
from pipeline.preprocess import preprocess_document
from pipeline.vision_extract import extract_vision_structured
from rules.bylaws import get_bylaw_profile
from rules.engine import evaluate_rules
from schemas.extracted import ExtractedDocument
from schemas.report import AnalysisReport, Summary
from services.openai_client import OpenAIClient
from services.storage import save_json

logger = get_logger(__name__)
settings = get_settings()


def _failure_code(extracted: dict[str, Any], bylaw_available: bool, source_mode: str, policy_result: dict[str, Any] | None = None) -> str:
    unresolved = [str(item) for item in extracted.get("unresolved_fields", [])]
    if not bylaw_available:
        return "BYLAW_SOURCE_MISSING"
    if str(source_mode).startswith("cad") and float(extracted.get("meta", {}).get("parser_confidence", 0.0) or 0.0) <= 0.01:
        return "CAD_PARSE_FAIL"
    if "UNIT_MISMATCH" in unresolved:
        return "UNIT_MISMATCH"
    if "DIMENSION_MISSING" in unresolved:
        return "DIMENSION_MISSING"
    if "LABEL_AMBIGUOUS" in unresolved:
        return "LABEL_AMBIGUOUS"
    if "LOW_CONFIDENCE" in unresolved:
        return "LOW_CONFIDENCE"
    if policy_result and not policy_result.get("allow_final_answer", True):
        return "LOW_CONFIDENCE"
    return ""


def _build_diagnostics(
    *,
    extracted: dict[str, Any],
    source_mode: str,
    rules_payload: list[dict[str, Any]],
    failure_reason_code: str,
) -> dict[str, Any]:
    return {
        "source_mode": source_mode,
        "parser_stage_logs": extracted.get("meta", {}).get("parser_stage_logs", []),
        "conversion_logs": extracted.get("meta", {}).get("source_trace", {}).get("conversion_logs", []),
        "extracted_snapshot": extracted,
        "confidence_snapshot": extracted.get("confidence_scores", extracted.get("confidence", {})),
        "rule_evaluation_trace": rules_payload,
        "top_failure_reason_code": failure_reason_code,
    }


def _summary(rule_results: list[dict[str, Any]]) -> Summary:
    total = len(rule_results)
    passed = len([r for r in rule_results if r["status"] == "pass"])
    failed = len([r for r in rule_results if r["status"] == "fail"])
    needs_review = len([r for r in rule_results if r["status"] == "needs_review"])
    return Summary(total_rules=total, passed=passed, failed=failed, needs_review=needs_review)


def run_pipeline_for_file(
    file_path: Path,
    bylaw_profile_id: str | None = None,
    analysis_id: str | None = None,
    manual_rotation_deg: float = 0,
    clarification_answers: dict[str, str] | None = None,
) -> AnalysisReport:
    run_id = analysis_id or uuid4().hex
    logger.info("Pipeline started for file=%s analysis_id=%s", file_path.name, run_id)

    ocr_blocks = []
    normalized: Dict[str, Any] = {}
    source_mode = "image_pipeline"

    if file_path.suffix.lower() in {".dwg", ".dxf"}:
        logger.info("Stage CAD ingest started")
        cleanup_temp = True
        try:
            cad = ingest_dwg(file_path, run_id)
            if cad.dxf_path is None:
                error_detail = "CAD conversion failed."
                if cad.conversion_logs:
                    non_empty_logs = [line for line in cad.conversion_logs if str(line).strip()]
                    if non_empty_logs:
                        error_detail = " | ".join(non_empty_logs[-3:])
                raise DwgIngestError(error_detail)
            parsed = parse_dxf_entities(cad.dxf_path)
            normalized = normalize_dwg_payload(parsed)
            parser_conf = float(normalized.get("meta", {}).get("parser_confidence", 0.0) or 0.0)
            source_mode = "cad_direct"

            if parser_conf < settings.dwg_parse_confidence_threshold:
                logger.warning("CAD parser confidence low (%.2f). Switching to rendered-image fallback.", parser_conf)
                if not cad.rendered_images:
                    raise DwgIngestError("Parser confidence low and CAD rendering fallback failed.")
                source_mode = "cad_render_fallback"
                fallback_parts: list[dict[str, Any]] = []
                fallback_ocr = []
                vision_client = OpenAIClient()
                for rendered in cad.rendered_images:
                    tiles = preprocess_document(rendered, run_id, manual_rotation_deg=0)
                    page_ocr = extract_ocr_blocks(tiles)
                    fallback_ocr.extend(page_ocr)
                    fallback_parts.extend(extract_vision_structured(tiles, page_ocr, vision_client))
                normalized = normalize_extracted(fallback_parts)
                ocr_blocks = fallback_ocr

            normalized.setdefault("meta", {})
            normalized["meta"]["source_mode"] = source_mode
            normalized["meta"]["source_trace"] = {
                "file": file_path.name,
                "dxf": str(cad.dxf_path) if cad.dxf_path else "",
                "conversion_logs": cad.conversion_logs,
            }
        except DwgIngestError as exc:
            cleanup_temp = False
            logger.exception("CAD ingest failed for %s", file_path.name)
            raise RuntimeError(str(exc)) from exc
        finally:
            if cleanup_temp:
                cleanup_dwg_temp(run_id)
    else:
        logger.info("Stage preprocess started")
        tiles = preprocess_document(file_path, run_id, manual_rotation_deg=manual_rotation_deg)
        logger.info("Stage preprocess completed tiles=%s", len(tiles))

        logger.info("Stage OCR started")
        ocr_blocks = extract_ocr_blocks(tiles)
        logger.info("Stage OCR completed blocks=%s", len(ocr_blocks))

        logger.info("Stage vision extraction started")
        vision_client = OpenAIClient()
        vision_parts = extract_vision_structured(tiles, ocr_blocks, vision_client)
        logger.info("Stage vision extraction completed tile_payloads=%s", len(vision_parts))

        logger.info("Stage normalization started")
        normalized = normalize_extracted(vision_parts)

    extracted_doc = ExtractedDocument(
        analysis_id=run_id,
        source_file=file_path.name,
        drawing_id=str(normalized.get("drawing_id") or run_id),
        units_detected=list(normalized.get("units_detected", [])),
        scale_info=dict(normalized.get("scale_info", {})),
        ocr_blocks=ocr_blocks,
        floors=normalized["floors"],
        rooms=normalized["rooms"],
        stairs=normalized["stairs"],
        lifts=normalized["lifts"],
        exits=normalized["exits"],
        corridors=normalized["corridors"],
        dimensions=normalized["dimensions"],
        confidence=normalized["confidence"],
        confidence_scores=dict(normalized.get("confidence_scores", {})),
        unresolved_fields=list(normalized.get("unresolved_fields", [])),
        meta=normalized["meta"],
    )
    logger.info("Stage normalization completed")

    gate_threshold = max(float(settings.confidence_threshold or 0.0), 0.85)
    confidence_scores = extracted_doc.confidence.model_dump()
    policy_result = evaluate_answer_policy(
        extracted_data=extracted_doc.model_dump(),
        required_fields=REQUIRED_FIELDS,
        confidence_scores=confidence_scores,
        confidence_threshold=gate_threshold,
        max_questions=settings.max_clarification_questions,
    )
    # For CAD-origin files, do not interrupt with clarification questions.
    # CAD should proceed to deterministic rules evaluation directly.
    if str(source_mode).startswith("cad"):
        gate_result = apply_decision_gate(
            extracted_data=extracted_doc.model_dump(),
            confidence_scores=confidence_scores,
            confidence_threshold=gate_threshold,
            required_fields=REQUIRED_FIELDS,
        )
        if not gate_result["allow_final_answer"]:
            policy_result["allow_final_answer"] = False
            policy_result["status"] = "NEEDS_CLARIFICATION"
            policy_result["missing_fields"] = sorted(set(policy_result["missing_fields"] + gate_result["missing_fields"]))
            policy_result["uncertain_fields"] = sorted(set(policy_result["uncertain_fields"] + gate_result["uncertain_fields"]))
    else:
        gate_result = apply_decision_gate(
            extracted_data=extracted_doc.model_dump(),
            confidence_scores=confidence_scores,
            confidence_threshold=gate_threshold,
            required_fields=REQUIRED_FIELDS,
        )
        if not gate_result["allow_final_answer"]:
            policy_result["allow_final_answer"] = False
            policy_result["status"] = "NEEDS_CLARIFICATION"
            policy_result["missing_fields"] = sorted(set(policy_result["missing_fields"] + gate_result["missing_fields"]))
            policy_result["uncertain_fields"] = sorted(set(policy_result["uncertain_fields"] + gate_result["uncertain_fields"]))

    if clarification_answers:
        for qid, answer in clarification_answers.items():
            if qid == "dimensions_unit":
                for dim in extracted_doc.dimensions:
                    dim.unit = answer.lower()
            if qid == "stairs_width_ft" and extracted_doc.stairs:
                parsed = parse_dimension_to_feet(answer, "ft")
                if parsed is not None:
                    extracted_doc.stairs[0].width_ft = parsed
            if qid == "exits_width_ft" and extracted_doc.exits:
                parsed = parse_dimension_to_feet(answer, "ft")
                if parsed is not None:
                    extracted_doc.exits[0].width_ft = parsed
            if qid == "corridors_width_ft" and extracted_doc.corridors:
                parsed = parse_dimension_to_feet(answer, "ft")
                if parsed is not None:
                    extracted_doc.corridors[0].width_ft = parsed
            if qid == "rooms_area_sqft" and extracted_doc.rooms:
                parsed = parse_dimension_to_feet(answer, "sqft")
                if parsed is not None:
                    extracted_doc.rooms[0].area_sqft = parsed

        # Re-evaluate policy after applying user answers.
        confidence_scores = extracted_doc.confidence.model_dump()
        policy_result = evaluate_answer_policy(
            extracted_data=extracted_doc.model_dump(),
            required_fields=REQUIRED_FIELDS,
            confidence_scores=confidence_scores,
            confidence_threshold=gate_threshold,
            max_questions=settings.max_clarification_questions,
            answered_question_ids=list(clarification_answers.keys()),
        )
        # If user supplied all required fields, do not loop on confidence-only uncertainty.
        required_qids = {field.replace(".", "_") for field in REQUIRED_FIELDS}
        if required_qids.issubset(set(clarification_answers.keys())):
            policy_result["allow_final_answer"] = True
            policy_result["status"] = "READY_FOR_DECISION"
            policy_result["questions"] = []
            policy_result["missing_fields"] = []
            policy_result["uncertain_fields"] = []
    if not policy_result["allow_final_answer"]:
        failure_reason = _failure_code(
            extracted=extracted_doc.model_dump(),
            bylaw_available=True,
            source_mode=source_mode,
            policy_result=policy_result,
        )
        diagnostics = _build_diagnostics(
            extracted=extracted_doc.model_dump(),
            source_mode=source_mode,
            rules_payload=[],
            failure_reason_code=failure_reason,
        )
        return AnalysisReport(
            success=True,
            analysis_id=run_id,
            status="NEEDS_CLARIFICATION",
            confidence_label="low",
            extracted_data=extracted_doc.model_dump(),
            what_i_found={
                "floors": len(extracted_doc.floors),
                "rooms": len(extracted_doc.rooms),
                "stairs": len(extracted_doc.stairs),
                "exits": len(extracted_doc.exits),
            },
            what_is_unclear=policy_result["missing_fields"] + policy_result["uncertain_fields"],
            questions_for_user=policy_result["questions"],
            failure_reason_code=failure_reason,
            diagnostics=diagnostics,
        )

    logger.info("Stage rules engine started")
    profile = get_bylaw_profile(bylaw_profile_id)
    try:
        rules = evaluate_rules(extracted_doc.model_dump(), profile)
        rules_payload = [rule.model_dump() for rule in rules]
    except RuntimeError as exc:
        if "BYLAW_SOURCE_MISSING" in str(exc):
            raise
        raise RuntimeError(f"RULE_MAPPING_ERROR: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"RULE_MAPPING_ERROR: {exc}") from exc
    logger.info("Stage rules engine completed total_rules=%s", len(rules_payload))
    failure_reason = _failure_code(
        extracted=extracted_doc.model_dump(),
        bylaw_available=True,
        source_mode=source_mode,
    )
    diagnostics = _build_diagnostics(
        extracted=extracted_doc.model_dump(),
        source_mode=source_mode,
        rules_payload=rules_payload,
        failure_reason_code=failure_reason,
    )

    report = AnalysisReport(
        success=True,
        analysis_id=run_id,
        status="READY_FOR_DECISION",
        confidence_label="high",
        extracted_data=extracted_doc.model_dump(),
        rule_results=rules,
        summary=_summary(rules_payload),
        what_i_found={
            "floors": len(extracted_doc.floors),
            "rooms": len(extracted_doc.rooms),
            "stairs": len(extracted_doc.stairs),
            "exits": len(extracted_doc.exits),
        },
        failure_reason_code=failure_reason,
        diagnostics=diagnostics,
    )
    return report


def persist_analysis(report: AnalysisReport, extracted_path: Path, report_path: Path) -> None:
    save_json(extracted_path, report.extracted_data)
    save_json(report_path, report.model_dump())
