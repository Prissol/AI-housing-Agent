from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import hashlib
import hmac
import os

import jwt
from pymongo.errors import DuplicateKeyError

from core.config import get_settings
from db.mongo import as_jsonable, users_collection, utcnow

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    current = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(current, expected)


def create_user(full_name: str, email: str, password: str, role: str = "user") -> dict[str, Any]:
    now = utcnow()
    payload = {
        "full_name": full_name.strip(),
        "email": email.strip().lower(),
        "password_hash": hash_password(password),
        "role": role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    try:
        result = users_collection().insert_one(payload)
    except DuplicateKeyError as exc:
        raise ValueError("Email already exists.") from exc
    created = users_collection().find_one({"_id": result.inserted_id})
    return as_jsonable(created) or {}


def issue_token(user: dict[str, Any]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(hours=24)
    claims = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "user"),
        "exp": int(expire_at.timestamp()),
        "iat": int(now.timestamp()),
    }
    if not settings.jwt_secret.strip():
        raise RuntimeError("JWT_SECRET is missing in environment.")
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.jwt_secret.strip():
        raise RuntimeError("JWT_SECRET is missing in environment.")
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = users_collection().find_one({"email": email.strip().lower(), "is_active": True})
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    users_collection().update_one({"_id": user["_id"]}, {"$set": {"last_login_at": utcnow(), "updated_at": utcnow()}})
    fresh = users_collection().find_one({"_id": user["_id"]})
    return as_jsonable(fresh)
