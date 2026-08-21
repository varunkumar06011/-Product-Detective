"""
Product Detective — Razorpay Payment Gateway Wrapper
Thin abstraction over the Razorpay Python SDK.
"""

import logging
import hmac
import hashlib
from typing import Optional, Dict, Any

import razorpay

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[razorpay.Client] = None


def _get_client() -> razorpay.Client:
    """Lazily initialise the Razorpay client (singleton)."""
    global _client
    if _client is None:
        _client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    return _client


def is_configured() -> bool:
    """True if real Razorpay keys are set (not the placeholder)."""
    return bool(
        settings.RAZORPAY_KEY_ID
        and not settings.RAZORPAY_KEY_ID.startswith("rzp_test_XXXX")
    )


def create_order(
    amount: Optional[int] = None,
    currency: str = None,
    receipt: str = None,
    notes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a Razorpay order.
    amount: in paise (e.g. 9900 = ₹99.00)
    Returns the order dict from Razorpay.
    """
    client = _get_client()
    amount = amount or settings.RAZORPAY_PRO_PLAN_AMOUNT
    currency = currency or settings.RAZORPAY_CURRENCY
    payload: Dict[str, Any] = {
        "amount": amount,
        "currency": currency,
        "payment_capture": 1,  # auto-capture
    }
    if receipt:
        payload["receipt"] = receipt
    if notes:
        payload["notes"] = notes
    order = client.order.create(payload)
    logger.info(f"Razorpay order created: {order.get('id')} for ₹{amount/100:.2f}")
    return order


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    """Verify the payment signature returned by Razorpay checkout."""
    client = _get_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except Exception as e:
        logger.error(f"Razorpay signature verification failed: {e}")
        return False


def verify_webhook_signature(
    webhook_body: bytes,
    webhook_signature: str,
) -> bool:
    """Verify a Razorpay webhook payload signature."""
    expected = hmac.new(
        key=settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        msg=webhook_body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, webhook_signature)


def fetch_payment(payment_id: str) -> Dict[str, Any]:
    """Fetch payment details by ID."""
    client = _get_client()
    return client.payment.fetch(payment_id)
