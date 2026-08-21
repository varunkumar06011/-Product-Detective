"""
Product Detective — Payments API Routes
Razorpay order creation, payment verification, and webhook handler.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from config.settings import settings
from modules import payment_gateway
from utils.auth import get_current_user, set_user_pro, is_user_pro, _get_db

logger = logging.getLogger(__name__)
router = APIRouter()

PRO_DURATION_DAYS = 365  # one-time Pro unlock lasts 1 year


# ─── Request / Response models ────────────────────────────────────────────────

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int          # paise
    currency: str
    key_id: str          # public key for frontend checkout
    user_email: str
    user_name: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class VerifyPaymentResponse(BaseModel):
    success: bool
    is_pro: bool
    message: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(user: dict = Depends(get_current_user)):
    """Create a Razorpay order for the Pro plan (one-time payment)."""
    if is_user_pro(user):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active Pro subscription.",
        )
    if not payment_gateway.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment gateway is not configured. Please contact support.",
        )
    receipt = f"pd_pro_{user['user_id']}_{int(datetime.now(timezone.utc).timestamp())}"
    try:
        order = payment_gateway.create_order(
            amount=settings.RAZORPAY_PRO_PLAN_AMOUNT,
            receipt=receipt,
            notes={"user_id": user["user_id"], "email": user["email"]},
        )
    except Exception as e:
        logger.error(f"Razorpay create_order failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create payment order. Please try again.",
        )
    # Persist order for reconciliation (non-fatal if DB is down)
    db = _get_db()
    if db is not None:
        try:
            await db.orders.update_one(
                {"razorpay_order_id": order["id"]},
                {"$set": {
                    "razorpay_order_id": order["id"],
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "amount": order["amount"],
                    "currency": order["currency"],
                    "status": order["status"],
                    "created_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
        except PyMongoError:
            pass  # order is still valid from Razorpay; just not persisted
    return CreateOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
        user_email=user["email"],
        user_name=user.get("name"),
    )


@router.post("/verify", response_model=VerifyPaymentResponse)
async def verify_payment(
    req: VerifyPaymentRequest,
    user: dict = Depends(get_current_user),
):
    """Verify a Razorpay payment signature and activate Pro."""
    # Verify the order belongs to this user (prevent verifying others' orders)
    db = _get_db()
    order_doc = None
    if db is not None:
        try:
            order_doc = await db.orders.find_one({"razorpay_order_id": req.razorpay_order_id})
        except PyMongoError:
            pass  # DB down — skip ownership check (signature still verified)
    if order_doc:
        if order_doc.get("user_id") != user["user_id"]:
            logger.warning(
                f"User {user['user_id']} attempted to verify order "
                f"{req.razorpay_order_id} belonging to {order_doc.get('user_id')}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This order does not belong to your account.",
            )
        # Idempotency: if already paid, return success without re-processing
        if order_doc.get("status") == "paid":
            return VerifyPaymentResponse(
                success=True,
                is_pro=is_user_pro(user),
                message="Payment already verified.",
            )

    valid = payment_gateway.verify_payment_signature(
        razorpay_order_id=req.razorpay_order_id,
        razorpay_payment_id=req.razorpay_payment_id,
        razorpay_signature=req.razorpay_signature,
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment signature verification failed.",
        )
    pro_until = datetime.now(timezone.utc) + timedelta(days=PRO_DURATION_DAYS)
    await set_user_pro(user["user_id"], is_pro=True, pro_until=pro_until)
    # Record payment (upsert to handle duplicate verification gracefully)
    if db is not None:
        try:
            await db.payments.update_one(
                {"razorpay_payment_id": req.razorpay_payment_id},
                {"$set": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "razorpay_order_id": req.razorpay_order_id,
                    "razorpay_payment_id": req.razorpay_payment_id,
                    "amount": settings.RAZORPAY_PRO_PLAN_AMOUNT,
                    "currency": settings.RAZORPAY_CURRENCY,
                    "status": "captured",
                    "pro_until": pro_until,
                    "verified_at": datetime.now(timezone.utc),
                }},
                upsert=True,
            )
            await db.orders.update_one(
                {"razorpay_order_id": req.razorpay_order_id},
                {"$set": {"status": "paid", "payment_id": req.razorpay_payment_id}},
            )
        except PyMongoError:
            pass  # Pro is activated in-memory; payment just not persisted
    logger.info(f"Pro activated for user {user['user_id']} until {pro_until}")
    return VerifyPaymentResponse(
        success=True,
        is_pro=True,
        message="Pro activated successfully. Enjoy full investigations!",
    )


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Razorpay webhook handler for payment.captured events.
    Verifies the signature and activates Pro as a backup to /verify.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not payment_gateway.verify_webhook_signature(body, signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature.",
        )
    event = json.loads(body)
    event_type = event.get("event")
    if event_type == "payment.captured":
        payment = event.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment.get("order_id")
        notes = payment.get("notes", {})
        user_id = notes.get("user_id")
        if user_id and order_id:
            pro_until = datetime.now(timezone.utc) + timedelta(days=PRO_DURATION_DAYS)
            await set_user_pro(user_id, is_pro=True, pro_until=pro_until)
            db = _get_db()
            if db is not None:
                try:
                    await db.payments.update_one(
                        {"razorpay_payment_id": payment.get("id")},
                        {"$set": {
                            "user_id": user_id,
                            "razorpay_order_id": order_id,
                            "razorpay_payment_id": payment.get("id"),
                            "amount": payment.get("amount"),
                            "currency": payment.get("currency"),
                            "status": "captured",
                            "pro_until": pro_until,
                            "via_webhook": True,
                            "verified_at": datetime.now(timezone.utc),
                        }},
                        upsert=True,
                    )
                    await db.orders.update_one(
                        {"razorpay_order_id": order_id},
                        {"$set": {"status": "paid", "payment_id": payment.get("id")}},
                    )
                except PyMongoError:
                    pass
            logger.info(f"Webhook: Pro activated for {user_id}")
    return {"status": "ok"}
