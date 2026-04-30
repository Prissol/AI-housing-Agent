from pipeline.dwg_normalize import normalize_dwg_payload
from policy.answer_policy import evaluate_answer_policy
from rules.bylaws import BylawProfile
from rules.engine import evaluate_rules


def test_dwg_normalize_converts_units_to_feet() -> None:
    payload = {
        "stairs": [{"name": "STAIR A", "width_ft": 1200, "unit": "mm", "source_trace": {"source": "dwg_entity"}}],
        "exits": [],
        "corridors": [],
        "rooms": [],
        "floors": [],
        "lifts": [],
        "dimensions": [{"label": "Exit Width", "value": 1500, "unit": "mm", "source": "dwg_dimension"}],
        "meta": {"parser_confidence": 0.8},
    }
    normalized = normalize_dwg_payload(payload)
    assert normalized["stairs"][0]["width_ft"] > 3.9
    assert normalized["dimensions"][0]["unit"] == "ft"


def test_rules_keep_dwg_evidence_points() -> None:
    extracted = {
        "stairs": [{"width_ft": 4.5, "source_trace": {"source": "dwg_entity", "entity_id": "A1", "layer": "STAIR"}}],
        "exits": [{"width_ft": 4.2, "source_trace": {"source": "dwg_entity", "entity_id": "A2", "layer": "EXIT"}}],
        "corridors": [{"width_ft": 6.1, "source_trace": {"source": "dwg_entity", "entity_id": "A3", "layer": "CORRIDOR"}}],
        "rooms": [{"area_sqft": 150.0, "source_trace": {"source": "dwg_entity", "entity_id": "A4", "layer": "ROOM"}}],
        "floors": [{"name": "Ground", "source_trace": {"source": "dwg_entity", "entity_id": "A5", "layer": "TEXT"}}],
        "lifts": [{"count": 1, "source_trace": {"source": "dwg_entity", "entity_id": "A6", "layer": "LIFT"}}],
    }
    rules = evaluate_rules(extracted, BylawProfile())
    assert any(rule.evidence.get("evidence_points") for rule in rules)


def test_policy_ready_when_confident_and_complete() -> None:
    extracted = {
        "source_file": "ok.dwg",
        "stairs": [{"width_ft": 4.5}],
        "exits": [{"width_ft": 4.2}],
        "corridors": [{"width_ft": 6.1}],
        "rooms": [{"area_sqft": 150}],
        "dimensions": [{"label": "W", "unit": "ft", "value": 4.0}],
    }
    policy = evaluate_answer_policy(
        extracted_data=extracted,
        required_fields=["stairs.width_ft", "exits.width_ft", "corridors.width_ft", "rooms.area_sqft", "dimensions.unit"],
        confidence_scores={"floors": 0.9, "rooms": 0.9, "circulation": 0.85, "dimensions": 0.9},
        confidence_threshold=0.8,
        max_questions=3,
    )
    assert policy["status"] == "READY_FOR_DECISION"
