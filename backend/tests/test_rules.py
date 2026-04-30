from rules.bylaws import BylawProfile
from rules.engine import evaluate_rules


def test_rules_engine_is_deterministic() -> None:
    extracted = {
        "stairs": [{"width_ft": 4.5}],
        "exits": [{"width_ft": 3.2}],
        "corridors": [{"width_ft": 5.0}],
        "rooms": [{"area_sqft": 120}],
        "floors": [{"name": "Ground"}, {"name": "First"}, {"name": "Second"}, {"name": "Third"}],
        "lifts": [{"count": 1}],
    }
    profile = BylawProfile()
    first = evaluate_rules(extracted, profile)
    second = evaluate_rules(extracted, profile)
    assert [r.model_dump() for r in first] == [r.model_dump() for r in second]
    assert any(r.rule_id == "EXIT_MIN_WIDTH" and r.status == "fail" for r in first)
