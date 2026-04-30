from __future__ import annotations

import json
from typing import Any

from core.config import get_settings
from core.logger import get_logger
from db.mongo import bylaw_clauses_collection, bylaw_sets_collection, utcnow

logger = get_logger(__name__)


DEFAULT_PROFILE_PAYLOAD = {
    "profile_id": "default",
    "min_stair_width_ft": 4.0,
    "min_exit_width_ft": 4.0,
    "min_corridor_width_ft": 5.0,
    "min_room_area_sqft": 80.0,
    "max_floors_without_lift": 3,
}


def _mongo_collection():
    settings = get_settings()
    if not settings.mongodb_uri.strip():
        return None
    try:
        from pymongo import MongoClient

        client = MongoClient(settings.mongodb_uri.strip(), serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        return client[settings.mongodb_db_name][settings.mongodb_bylaws_collection]
    except Exception as exc:
        logger.warning("MongoDB unavailable for bylaws, falling back to JSON. reason=%s", exc)
        return None


def _json_profiles_payload() -> dict[str, Any]:
    settings = get_settings()
    path = settings.bylaw_profiles_path
    if not path.exists():
        return {"default": DEFAULT_PROFILE_PAYLOAD}
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_bylaw_profiles_seeded() -> None:
    collection = _mongo_collection()
    if collection is None:
        return
    if collection.count_documents({}) > 0:
        return
    payload = _json_profiles_payload()
    docs = []
    for key, raw in payload.items():
        profile_id = str(raw.get("profile_id", key))
        docs.append(
            {
                "profile_id": profile_id,
                "min_stair_width_ft": float(raw.get("min_stair_width_ft", DEFAULT_PROFILE_PAYLOAD["min_stair_width_ft"])),
                "min_exit_width_ft": float(raw.get("min_exit_width_ft", DEFAULT_PROFILE_PAYLOAD["min_exit_width_ft"])),
                "min_corridor_width_ft": float(raw.get("min_corridor_width_ft", DEFAULT_PROFILE_PAYLOAD["min_corridor_width_ft"])),
                "min_room_area_sqft": float(raw.get("min_room_area_sqft", DEFAULT_PROFILE_PAYLOAD["min_room_area_sqft"])),
                "max_floors_without_lift": int(
                    raw.get("max_floors_without_lift", DEFAULT_PROFILE_PAYLOAD["max_floors_without_lift"])
                ),
            }
        )
    if docs:
        collection.insert_many(docs)
    _seed_bylaw_sets_and_clauses(docs)


def _seed_bylaw_sets_and_clauses(seed_profiles: list[dict[str, Any]]) -> None:
    try:
        if bylaw_sets_collection().count_documents({}) > 0:
            return
        now = utcnow()
        for profile in seed_profiles:
            set_doc = {
                "name": profile["profile_id"],
                "version": "2025.1",
                "city": "Multan",
                "status": "active",
                "created_at": now,
            }
            set_id = bylaw_sets_collection().insert_one(set_doc).inserted_id
            clauses = [
                {
                    "bylaw_set_id": str(set_id),
                    "clause_id": "STAIR_MIN_WIDTH",
                    "text": "Minimum stair clear width",
                    "field_path": "stairs.width_ft",
                    "operator": ">=",
                    "threshold": profile["min_stair_width_ft"],
                    "unit": "ft",
                    "severity": "high",
                },
                {
                    "bylaw_set_id": str(set_id),
                    "clause_id": "EXIT_MIN_WIDTH",
                    "text": "Minimum exit clear width",
                    "field_path": "exits.width_ft",
                    "operator": ">=",
                    "threshold": profile["min_exit_width_ft"],
                    "unit": "ft",
                    "severity": "high",
                },
                {
                    "bylaw_set_id": str(set_id),
                    "clause_id": "CORRIDOR_MIN_WIDTH",
                    "text": "Minimum corridor clear width",
                    "field_path": "corridors.width_ft",
                    "operator": ">=",
                    "threshold": profile["min_corridor_width_ft"],
                    "unit": "ft",
                    "severity": "medium",
                },
                {
                    "bylaw_set_id": str(set_id),
                    "clause_id": "ROOM_MIN_AREA",
                    "text": "Minimum room area",
                    "field_path": "rooms.area_sqft",
                    "operator": ">=",
                    "threshold": profile["min_room_area_sqft"],
                    "unit": "sqft",
                    "severity": "medium",
                },
            ]
            if clauses:
                bylaw_clauses_collection().insert_many(clauses)
    except Exception as exc:
        logger.warning("Failed seeding bylaw_sets/bylaw_clauses: %s", exc)


def get_bylaw_profile_payload(profile_id: str | None) -> dict[str, Any]:
    requested_id = str(profile_id or "default")
    collection = _mongo_collection()
    if collection is not None:
        doc = collection.find_one({"profile_id": requested_id}, {"_id": 0})
        if not doc and requested_id != "default":
            doc = collection.find_one({"profile_id": "default"}, {"_id": 0})
        if doc:
            return doc

    payload = _json_profiles_payload()
    raw = payload.get(requested_id) or payload.get("default") or DEFAULT_PROFILE_PAYLOAD
    return {
        "profile_id": str(raw.get("profile_id", requested_id)),
        "min_stair_width_ft": float(raw.get("min_stair_width_ft", DEFAULT_PROFILE_PAYLOAD["min_stair_width_ft"])),
        "min_exit_width_ft": float(raw.get("min_exit_width_ft", DEFAULT_PROFILE_PAYLOAD["min_exit_width_ft"])),
        "min_corridor_width_ft": float(raw.get("min_corridor_width_ft", DEFAULT_PROFILE_PAYLOAD["min_corridor_width_ft"])),
        "min_room_area_sqft": float(raw.get("min_room_area_sqft", DEFAULT_PROFILE_PAYLOAD["min_room_area_sqft"])),
        "max_floors_without_lift": int(
            raw.get("max_floors_without_lift", DEFAULT_PROFILE_PAYLOAD["max_floors_without_lift"])
        ),
    }


def get_bylaw_clauses(profile_id: str | None, only_enforceable: bool = True) -> list[dict[str, Any]]:
    requested_id = str(profile_id or "default")
    try:
        target_set = bylaw_sets_collection().find_one({"name": requested_id}, sort=[("created_at", -1)])
        if not target_set and requested_id != "default":
            target_set = bylaw_sets_collection().find_one({"name": "default"}, sort=[("created_at", -1)])
        if target_set:
            clauses = list(bylaw_clauses_collection().find({"bylaw_set_id": str(target_set["_id"])}))
            if clauses:
                if only_enforceable:
                    clauses = [
                        clause
                        for clause in clauses
                        if str(clause.get("evaluation_mode", "deterministic")).lower() != "manual"
                    ]
                return clauses
    except Exception as exc:
        logger.warning("Unable to load bylaw_clauses from MongoDB for profile=%s: %s", requested_id, exc)
    return []
