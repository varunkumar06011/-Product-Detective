"""
Product Detective — Supabase (PostgreSQL) Database Utility
Async connection pool for auth & payments tables.

Tables created automatically on startup:
  - users    : user accounts with Pro status
  - orders   : Razorpay orders
  - payments : verified payments
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

import asyncpg

from config.settings import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


def _parse_db_url(url: str) -> dict:
    """Parse a PostgreSQL connection URL into asyncpg connect kwargs."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/") or "postgres",
    }


async def init_supabase():
    """Initialise the PostgreSQL connection pool and create tables."""
    global _pool
    url = settings.SUPABASE_DB_URL
    if not url:
        logger.warning("SUPABASE_DB_URL not set — auth/payments will be unavailable.")
        return False
    try:
        conn_kwargs = _parse_db_url(url)
        _pool = await asyncpg.create_pool(
            min_size=2,
            max_size=10,
            command_timeout=10,
            statement_cache_size=0,  # required for PgBouncer (Supabase pooler)
            **conn_kwargs,
        )
        async with _pool.acquire() as conn:
            await conn.execute("SELECT 1")
        await _create_tables()
        logger.info("✅ Supabase PostgreSQL connected (auth & payments ready).")
        return True
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        _pool = None
        return False


async def close_supabase():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("Supabase PostgreSQL disconnected.")


async def _create_tables():
    """Create tables if they don't exist."""
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                is_pro        BOOLEAN NOT NULL DEFAULT FALSE,
                pro_until     TIMESTAMPTZ,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                razorpay_order_id TEXT PRIMARY KEY,
                user_id           TEXT NOT NULL REFERENCES users(user_id),
                email             TEXT NOT NULL,
                amount            INTEGER NOT NULL,
                currency          TEXT NOT NULL DEFAULT 'INR',
                status            TEXT NOT NULL DEFAULT 'created',
                payment_id        TEXT,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                razorpay_payment_id TEXT PRIMARY KEY,
                user_id             TEXT NOT NULL REFERENCES users(user_id),
                email               TEXT NOT NULL,
                razorpay_order_id   TEXT NOT NULL,
                amount              INTEGER NOT NULL,
                currency            TEXT NOT NULL DEFAULT 'INR',
                status              TEXT NOT NULL DEFAULT 'captured',
                pro_until           TIMESTAMPTZ,
                via_webhook         BOOLEAN NOT NULL DEFAULT FALSE,
                verified_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        logger.info("Supabase tables ready (users, orders, payments).")


def get_pool() -> Optional[asyncpg.Pool]:
    """Return the connection pool or None if not initialised."""
    return _pool


def is_available() -> bool:
    """True if Supabase pool is initialised."""
    return _pool is not None


# ─── User CRUD ────────────────────────────────────────────────────────────────

async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, name, password_hash, is_pro, pro_until, created_at "
            "FROM users WHERE email = $1",
            email.lower(),
        )
        return dict(row) if row else None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT user_id, email, name, password_hash, is_pro, pro_until, created_at "
            "FROM users WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None


async def create_user(email: str, name: str, password_hash: str) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None
    user_id = f"u_{email.lower().replace('@', '_at_').replace('.', '_')}"
    async with _pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO users (user_id, email, name, password_hash) "
                "VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (user_id) DO NOTHING",
                user_id, email.lower(), name, password_hash,
            )
        except asyncpg.UniqueViolationError:
            # Email already exists (race condition caught by unique constraint)
            return None
        # Fetch the actual stored row (handles race: might be another user's hash)
        row = await conn.fetchrow(
            "SELECT user_id, email, name, password_hash, is_pro, pro_until, created_at "
            "FROM users WHERE user_id = $1",
            user_id,
        )
        return dict(row) if row else None


async def set_user_pro(user_id: str, is_pro: bool, pro_until=None):
    if not is_available():
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_pro = $1, pro_until = $2 WHERE user_id = $3",
            is_pro, pro_until, user_id,
        )


# ─── Order CRUD ───────────────────────────────────────────────────────────────

async def upsert_order(order_data: Dict[str, Any]):
    if not is_available():
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO orders (razorpay_order_id, user_id, email, amount, currency, status, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7) "
            "ON CONFLICT (razorpay_order_id) DO UPDATE SET "
            "  user_id = EXCLUDED.user_id, email = EXCLUDED.email, "
            "  amount = EXCLUDED.amount, currency = EXCLUDED.currency, "
            "  status = EXCLUDED.status",
            order_data["razorpay_order_id"],
            order_data["user_id"],
            order_data["email"],
            order_data["amount"],
            order_data.get("currency", "INR"),
            order_data.get("status", "created"),
            order_data.get("created_at", datetime.now(timezone.utc)),
        )


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    if not is_available():
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT razorpay_order_id, user_id, email, amount, currency, status, payment_id, created_at "
            "FROM orders WHERE razorpay_order_id = $1",
            order_id,
        )
        return dict(row) if row else None


async def mark_order_paid(order_id: str, payment_id: str):
    if not is_available():
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE orders SET status = 'paid', payment_id = $1 "
            "WHERE razorpay_order_id = $2",
            payment_id, order_id,
        )


# ─── Payment CRUD ─────────────────────────────────────────────────────────────

async def upsert_payment(payment_data: Dict[str, Any]):
    if not is_available():
        return
    async with _pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO payments (razorpay_payment_id, user_id, email, razorpay_order_id, "
            "  amount, currency, status, pro_until, via_webhook, verified_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) "
            "ON CONFLICT (razorpay_payment_id) DO UPDATE SET "
            "  status = EXCLUDED.status, pro_until = EXCLUDED.pro_until, "
            "  verified_at = EXCLUDED.verified_at",
            payment_data["razorpay_payment_id"],
            payment_data["user_id"],
            payment_data.get("email", ""),
            payment_data["razorpay_order_id"],
            payment_data.get("amount", 0),
            payment_data.get("currency", "INR"),
            payment_data.get("status", "captured"),
            payment_data.get("pro_until"),
            payment_data.get("via_webhook", False),
            payment_data.get("verified_at", datetime.now(timezone.utc)),
        )
