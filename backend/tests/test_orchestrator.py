from rules.bylaws import BylawProfile
from rules.engine import evaluate_rules
from schemas.report import AnalysisReport, Summary
from policy.answer_policy import evaluate_answer_policy


def test_missing_dimensions_goes_needs_review() -> None:
    extracted = {
        "stairs": [{}],
        "exits": [{}],
        "corridors": [{}],
        "rooms": [{}],
        "floors": [],
        "lifts": [],
    }
    results = evaluate_rules(extracted, BylawProfile())
    assert any(item.status == "needs_review" for item in results)


def test_report_schema_validates() -> None:
    payload = AnalysisReport(
        success=True,
        analysis_id="abc",
        extracted_data={"floors": []},
        rule_results=[],
        summary=Summary(total_rules=0, passed=0, failed=0, needs_review=0),
    )
    assert payload.analysis_id == "abc"


def test_profile_lookup_from_json() -> None:
    from rules.bylaws import get_bylaw_profile

    profile = get_bylaw_profile("dha_standard")
    assert profile.profile_id == "dha_standard"
    assert profile.min_room_area_sqft >= 80.0


def test_policy_triggers_clarification_when_missing_required_fields() -> None:
    extracted = {
        "source_file": "a.dwg",
        "stairs": [],
        "exits": [],
        "corridors": [],
        "rooms": [],
        "dimensions": [],
    }
    policy = evaluate_answer_policy(
        extracted_data=extracted,
        required_fields=["stairs.width_ft", "dimensions.unit"],
        confidence_scores={"dimensions": 0.4},
        confidence_threshold=0.8,
        max_questions=3,
    )
    assert policy["status"] == "NEEDS_CLARIFICATION"
    assert policy["allow_final_answer"] is False
    assert len(policy["questions"]) <= 3
