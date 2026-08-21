"""
Product Detective — Auth & Billing Dependencies
FastAPI dependencies for extracting the current user (optional/required)
and checking Pro subscription status.

All DB helpers are resilient to MongoDB being unavailable — they return
None / no-op instead of crashing, so the app still works in degraded mode.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo.errors import PyMongoError

from modules.auth_service import decode_access_token

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# ─── User DB helpers ──────────────────────────────────────────────────────────
# All helpers catch PyMongoError (includes ServerSelectionTimeoutError,
# AutoReconnect, etc.) so the app works in degraded mode without MongoDB.

def _get_db():
    """Return the DB instance or None if not initialised."""
    try:
        from utils.database import get_db
        return get_db()
    except RuntimeError:
        return None


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if db is None:
        return None
    try:
        return await db.users.find_one({"email": email.lower()}, {"_id": 0})
    except PyMongoError:
        return None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if db is None:
        return None
    try:
        return await db.users.find_one({"user_id": user_id}, {"_id": 0})
    except PyMongoError:
        return None


async def create_user(email: str, name: str, password_hash: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if db is None:
        return None
    user_id = f"u_{email.lower().replace('@', '_at_').replace('.', '_')}"
    doc = {
        "user_id": user_id,
        "email": email.lower(),
        "name": name,
        "password_hash": password_hash,
        "is_pro": False,
        "pro_until": None,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        await db.users.update_one(
            {"user_id": user_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        # Re-fetch to get the actual stored doc (handles TOCTOU race)
        stored = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        return stored or doc
    except PyMongoError:
        return None


async def set_user_pro(user_id: str, is_pro: bool, pro_until: Optional[datetime] = None):
    db = _get_db()
    if db is None:
        return
    try:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"is_pro": is_pro, "pro_until": pro_until}},
        )
    except PyMongoError:
        pass


# ─── Dependencies ─────────────────────────────────────────────────────────────

async def get_current_user_optional(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """
    Returns the user dict if a valid JWT is present, else None.
    Never raises — use for endpoints that work for both anon + authed users.
    Returns None gracefully if DB is unavailable (degraded mode).
    """
    if creds is None or creds.credentials is None:
        return None
    payload = decode_access_token(creds.credentials)
    if payload is None:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = await get_user_by_id(user_id)
    if user is None:
        # DB down or user deleted — treat as anonymous
        return None
    if _pro_expired(user):
        await set_user_pro(user["user_id"], False, None)
        user["is_pro"] = False
        user["pro_until"] = None
    return user


async def get_current_user(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional),
) -> Dict[str, Any]:
    """Requires a valid JWT. Raises 401 if missing/invalid."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )
    return user


def _pro_expired(user: Dict[str, Any]) -> bool:
    """True if user had pro but it has expired."""
    if not user.get("is_pro"):
        return False
    pro_until = user.get("pro_until")
    if pro_until is None:
        return False
    if isinstance(pro_until, str):
        pro_until = datetime.fromisoformat(pro_until)
    if pro_until.tzinfo is None:
        pro_until = pro_until.replace(tzinfo=timezone.utc)
    return pro_until < datetime.now(timezone.utc)


def is_user_pro(user: Optional[Dict[str, Any]]) -> bool:
    """Check Pro status (handles None / expired gracefully)."""
    if not user:
        return False
    if _pro_expired(user):
        return False
    return bool(user.get("is_pro"))
