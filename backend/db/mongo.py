from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    settings = get_settings()
    if not settings.mongodb_uri.strip():
        raise RuntimeError("MONGODB_URI is missing. Configure it in backend/.env")
    return MongoClient(
        settings.mongodb_uri.strip(),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000,
    )


def get_db() -> Database:
    settings = get_settings()
    return get_client()[settings.mongodb_db_name]


def users_collection() -> Collection:
    return get_db()["users"]


def analysis_history_collection() -> Collection:
    return get_db()["analysis_history"]


def chat_logs_collection() -> Collection:
    return get_db()["chat_logs"]


def report_metadata_collection() -> Collection:
    return get_db()["report_metadata"]


def bylaw_sets_collection() -> Collection:
    return get_db()["bylaw_sets"]


def bylaw_clauses_collection() -> Collection:
    return get_db()["bylaw_clauses"]


def ensure_indexes() -> None:
    try:
        users_collection().create_index([("email", ASCENDING)], unique=True)
        analysis_history_collection().create_index([("analysis_id", ASCENDING)], unique=True)
        analysis_history_collection().create_index([("user_id", ASCENDING)])
        chat_logs_collection().create_index([("session_id", ASCENDING)])
        chat_logs_collection().create_index([("analysis_id", ASCENDING)])
        chat_logs_collection().create_index([("user_id", ASCENDING)])
        report_metadata_collection().create_index([("report_id", ASCENDING)], unique=True)
        report_metadata_collection().create_index([("analysis_id", ASCENDING)])
        report_metadata_collection().create_index([("user_id", ASCENDING)])
        bylaw_sets_collection().create_index([("name", ASCENDING), ("version", ASCENDING)], unique=True)
        bylaw_clauses_collection().create_index([("bylaw_set_id", ASCENDING)])
    except Exception as exc:
        logger.warning("MongoDB index initialization skipped: %s", exc)


def as_jsonable(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None
    transformed = dict(document)
    if "_id" in transformed:
        transformed["_id"] = str(transformed["_id"])
    if "user_id" in transformed and transformed["user_id"] is not None:
        transformed["user_id"] = str(transformed["user_id"])
    return transformed
