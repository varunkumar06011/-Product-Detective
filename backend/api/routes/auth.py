"""
Product Detective — Auth API Routes
Signup, login, and profile (/me) endpoints.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field

from modules.auth_service import hash_password, verify_password, create_access_token
from utils.auth import (
    get_user_by_email,
    create_user,
    get_current_user,
    is_user_pro,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / Response models ────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    is_pro: bool
    pro_until: datetime | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserOut


def _user_out(user: dict) -> dict:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "is_pro": is_user_pro(user),
        "pro_until": user.get("pro_until"),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    existing = await get_user_by_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    password_hash = hash_password(req.password)
    user = await create_user(
        email=req.email,
        name=req.name,
        password_hash=password_hash,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable. Please try again later.",
        )
    # Race condition guard: if the returned doc's password hash doesn't match,
    # another user was created with this email first
    if user.get("password_hash") != password_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    token = create_access_token({"sub": user["user_id"], "email": user["email"]})
    logger.info(f"New user signed up: {user['email']}")
    return AuthResponse(token=token, user=UserOut(**_user_out(user)))


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = await get_user_by_email(req.email)
    if not user or not verify_password(req.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token({"sub": user["user_id"], "email": user["email"]})
    return AuthResponse(token=token, user=UserOut(**_user_out(user)))


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**_user_out(user))
