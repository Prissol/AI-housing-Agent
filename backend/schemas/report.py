from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    rule_id: str
    status: Literal["pass", "fail", "needs_review"]
    expected: Any = None
    observed: Any = None
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    clause_ref: str


class Summary(BaseModel):
    total_rules: int
    passed: int
    failed: int
    needs_review: int


class AnalysisReport(BaseModel):
    success: bool = True
    analysis_id: str
    status: Literal["READY_FOR_DECISION", "NEEDS_CLARIFICATION"] = "READY_FOR_DECISION"
    confidence_label: Literal["high", "low"] = "high"
    extracted_data: Dict[str, Any]
    rule_results: List[RuleResult] = Field(default_factory=list)
    summary: Summary = Field(default_factory=lambda: Summary(total_rules=0, passed=0, failed=0, needs_review=0))
    what_i_found: Dict[str, Any] = Field(default_factory=dict)
    what_is_unclear: List[str] = Field(default_factory=list)
    questions_for_user: List[Dict[str, Any]] = Field(default_factory=list)
    failure_reason_code: str = ""
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
