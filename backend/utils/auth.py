"""
Product Detective — Auth & Billing Dependencies
FastAPI dependencies for extracting the current user (optional/required)
and checking Pro subscription status.

Uses Supabase (PostgreSQL) for user/order/payment storage.
All helpers return None / no-op if Supabase is unavailable (degraded mode).
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from modules.auth_service import decode_access_token
from utils import supabase_db

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


# ─── User helpers (delegated to supabase_db) ──────────────────────────────────

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return await supabase_db.get_user_by_email(email)


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return await supabase_db.get_user_by_id(user_id)


async def create_user(email: str, name: str, password_hash: str) -> Optional[Dict[str, Any]]:
    return await supabase_db.create_user(email, name, password_hash)


async def set_user_pro(user_id: str, is_pro: bool, pro_until: Optional[datetime] = None):
    await supabase_db.set_user_pro(user_id, is_pro, pro_until)


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
    if isinstance(pro_until, datetime) and pro_until.tzinfo is None:
        pro_until = pro_until.replace(tzinfo=timezone.utc)
    return pro_until < datetime.now(timezone.utc)


def is_user_pro(user: Optional[Dict[str, Any]]) -> bool:
    """Check Pro status (handles None / expired gracefully)."""
    if not user:
        return False
    if _pro_expired(user):
        return False
    return bool(user.get("is_pro"))
