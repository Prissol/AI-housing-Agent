from typing import Any, Dict, List

from rules.bylaws import BylawProfile
from rules.bylaw_repository import get_bylaw_clauses
from rules.evidence import build_evidence, merge_evidence
from schemas.report import RuleResult


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _extract_observed_numeric(extracted: Dict[str, Any], field_path: str) -> tuple[float | None, list[dict[str, Any]]]:
    if field_path == "floors.count":
        floors = extracted.get("floors", [])
        if isinstance(floors, list):
            return float(len(floors)), floors
        return None, []
    if field_path.startswith("dimensions."):
        dimensions = extracted.get("dimensions", [])
        if not isinstance(dimensions, list):
            return None, []
        if field_path == "dimensions.height_ft_max":
            candidates = [
                _to_float(item.get("value"))
                for item in dimensions
                if "height" in str(item.get("label", "")).lower()
            ]
            values = [v for v in candidates if v is not None]
            return (max(values), dimensions) if values else (None, dimensions)
        token_map = {
            "dimensions.front_setback_ft_min": ["front", "setback", "cos"],
            "dimensions.rear_setback_ft_min": ["rear", "setback", "cos"],
            "dimensions.side_setback_ft_min": ["side", "setback", "cos"],
        }
        wanted = token_map.get(field_path)
        if wanted:
            values: list[float] = []
            for item in dimensions:
                label = str(item.get("label", "")).lower()
                if wanted[0] in label and any(token in label for token in wanted[1:]):
                    parsed = _to_float(item.get("value"))
                    if parsed is not None:
                        values.append(parsed)
            return (min(values), dimensions) if values else (None, dimensions)
    root, _, prop = field_path.partition(".")
    entities = extracted.get(root, [])
    if not isinstance(entities, list):
        return None, []
    numeric_values = []
    for item in entities:
        numeric = _to_float(item.get(prop))
        if numeric is not None:
            numeric_values.append(numeric)
    if not numeric_values:
        return None, entities
    return min(numeric_values), entities


def _evaluate_db_clause(extracted: Dict[str, Any], clause: Dict[str, Any]) -> RuleResult:
    clause_id = str(clause.get("clause_id") or clause.get("_id") or "UNKNOWN_RULE")
    clause_ref = str(clause.get("clause_ref") or clause.get("text") or clause_id)
    field_path = str(clause.get("field_path") or "")
    operator = str(clause.get("operator") or ">=").strip()
    threshold = _to_float(clause.get("threshold"))

    if not field_path or threshold is None:
        return RuleResult(
            rule_id=clause_id,
            status="needs_review",
            expected=threshold,
            observed=None,
            reason="Clause configuration incomplete in database (field_path/threshold missing).",
            evidence=build_evidence(field_path or "unknown", None, threshold),
            clause_ref=clause_ref,
        )

    if field_path == "floors.count_without_lift":
        floors = extracted.get("floors", [])
        lifts = extracted.get("lifts", [])
        floor_count = len(floors) if isinstance(floors, list) else 0
        has_lift = any((item.get("count") or 0) > 0 for item in lifts) or (isinstance(lifts, list) and len(lifts) > 0)
        if floor_count == 0:
            status = "needs_review"
            reason = "Floor count missing; cannot validate lift requirement."
        elif has_lift:
            status = "pass"
            reason = f"Floors detected: {floor_count}. Lift present, so without-lift limit check is satisfied."
        else:
            comparator = {
                ">=": lambda a, b: a >= b,
                ">": lambda a, b: a > b,
                "<=": lambda a, b: a <= b,
                "<": lambda a, b: a < b,
                "==": lambda a, b: a == b,
                "=": lambda a, b: a == b,
            }.get(operator)
            if comparator is None:
                status = "needs_review"
                reason = f"Unsupported operator '{operator}' in clause configuration."
            else:
                status = "pass" if comparator(float(floor_count), threshold) else "fail"
                reason = f"Floors detected: {floor_count}. Lift absent; required floors {operator} {threshold}."
        return RuleResult(
            rule_id=clause_id,
            status=status,
            expected=threshold,
            observed={"floors": floor_count, "has_lift": has_lift},
            reason=reason,
            evidence=merge_evidence(
                build_evidence("floors/lifts", {"floors": floor_count, "has_lift": has_lift}, threshold),
                (floors if isinstance(floors, list) else []) + (lifts if isinstance(lifts, list) else []),
            ),
            clause_ref=clause_ref,
        )

    observed, source_entities = _extract_observed_numeric(extracted, field_path)
    if observed is None:
        return RuleResult(
            rule_id=clause_id,
            status="needs_review",
            expected=threshold,
            observed=None,
            reason=f"Insufficient measurable evidence for {field_path}.",
            evidence=merge_evidence(build_evidence(field_path, observed, threshold), source_entities),
            clause_ref=clause_ref,
        )

    comparator = {
        ">=": lambda a, b: a >= b,
        ">": lambda a, b: a > b,
        "<=": lambda a, b: a <= b,
        "<": lambda a, b: a < b,
        "==": lambda a, b: a == b,
        "=": lambda a, b: a == b,
    }.get(operator)
    if comparator is None:
        return RuleResult(
            rule_id=clause_id,
            status="needs_review",
            expected=threshold,
            observed=observed,
            reason=f"Unsupported operator '{operator}' in clause configuration.",
            evidence=merge_evidence(build_evidence(field_path, observed, threshold), source_entities),
            clause_ref=clause_ref,
        )

    passed = comparator(observed, threshold)
    status = "pass" if passed else "fail"
    return RuleResult(
        rule_id=clause_id,
        status=status,
        expected=threshold,
        observed=observed,
        reason=f"{field_path} observed: {observed}; required {operator} {threshold}.",
        evidence=merge_evidence(build_evidence(field_path, observed, threshold), source_entities),
        clause_ref=clause_ref,
    )


def evaluate_rules(extracted: Dict[str, Any], bylaw: BylawProfile) -> List[RuleResult]:
    results: List[RuleResult] = []
    db_clauses = get_bylaw_clauses(bylaw.profile_id, only_enforceable=True)
    if not db_clauses:
        raise RuntimeError("BYLAW_SOURCE_MISSING: No enforceable bylaw clauses found for active profile.")
    seen_rule_ids: set[str] = set()
    for clause in db_clauses:
        result = _evaluate_db_clause(extracted, clause)
        if result.rule_id in seen_rule_ids:
            suffix = str(clause.get("_id") or "")
            if suffix:
                result.rule_id = f"{result.rule_id}_{suffix[-6:]}"
        seen_rule_ids.add(result.rule_id)
        results.append(result)
    return results
