from __future__ import annotations

from db.mongo import bylaw_clauses_collection, bylaw_sets_collection, utcnow


def seed() -> None:
    now = utcnow()
    residential = bylaw_sets_collection().find_one({"name": "dha_residential", "version": "2025.1"})
    if not residential:
        res_id = bylaw_sets_collection().insert_one(
            {"name": "dha_residential", "version": "2025.1", "city": "Multan", "status": "active", "created_at": now}
        ).inserted_id
        bylaw_clauses_collection().insert_many(
            [
                {
                    "bylaw_set_id": str(res_id),
                    "clause_id": "STAIR_MIN_WIDTH",
                    "text": "Minimum stair clear width",
                    "field_path": "stairs.width_ft",
                    "operator": ">=",
                    "threshold": 4.0,
                    "unit": "ft",
                    "severity": "high",
                },
                {
                    "bylaw_set_id": str(res_id),
                    "clause_id": "EXIT_MIN_WIDTH",
                    "text": "Minimum exit clear width",
                    "field_path": "exits.width_ft",
                    "operator": ">=",
                    "threshold": 4.0,
                    "unit": "ft",
                    "severity": "high",
                },
                {
                    "bylaw_set_id": str(res_id),
                    "clause_id": "CORRIDOR_MIN_WIDTH",
                    "text": "Minimum corridor clear width",
                    "field_path": "corridors.width_ft",
                    "operator": ">=",
                    "threshold": 5.0,
                    "unit": "ft",
                    "severity": "medium",
                },
                {
                    "bylaw_set_id": str(res_id),
                    "clause_id": "ROOM_MIN_AREA",
                    "text": "Minimum room area",
                    "field_path": "rooms.area_sqft",
                    "operator": ">=",
                    "threshold": 90.0,
                    "unit": "sqft",
                    "severity": "medium",
                },
            ]
        )

    commercial = bylaw_sets_collection().find_one({"name": "dha_commercial", "version": "2025.1"})
    if not commercial:
        com_id = bylaw_sets_collection().insert_one(
            {"name": "dha_commercial", "version": "2025.1", "city": "Multan", "status": "active", "created_at": now}
        ).inserted_id
        bylaw_clauses_collection().insert_many(
            [
                {
                    "bylaw_set_id": str(com_id),
                    "clause_id": "STAIR_MIN_WIDTH",
                    "text": "Minimum stair clear width",
                    "field_path": "stairs.width_ft",
                    "operator": ">=",
                    "threshold": 5.0,
                    "unit": "ft",
                    "severity": "high",
                },
                {
                    "bylaw_set_id": str(com_id),
                    "clause_id": "EXIT_MIN_WIDTH",
                    "text": "Minimum exit clear width",
                    "field_path": "exits.width_ft",
                    "operator": ">=",
                    "threshold": 5.0,
                    "unit": "ft",
                    "severity": "high",
                },
            ]
        )

    print("Bylaw sets seeded.")


if __name__ == "__main__":
    seed()
