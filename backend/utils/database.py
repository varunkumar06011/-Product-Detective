"""
Product Detective — MongoDB Async Database Utility
Uses Motor (async PyMongo) for non-blocking database operations.
Collections:
  - investigations   : full investigation results keyed by case_id
  - products         : scraped product data cache
  - reviews          : raw review documents
  - feedback         : user feedback on verdicts (for future RLHF)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError, OperationFailure

from config.settings import settings

logger = logging.getLogger(__name__)

# Module-level client (single connection pool for the app lifetime)
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db():
    """Initialise the MongoDB connection pool and create indexes."""
    global _client, _db
    try:
        _client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=20,
        )
        _db = _client[settings.MONGO_DB]
        # Verify connection
        await _client.admin.command("ping")
        logger.info(f"✅ MongoDB connected: {settings.MONGO_URI}/{settings.MONGO_DB}")
        await _create_indexes()
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


async def disconnect_db():
    """Close the MongoDB connection pool."""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB disconnected.")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database instance (dependency injection friendly)."""
    if _db is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _db


async def _create_indexes():
    """Create indexes for performance-critical queries."""
    db = get_db()
    try:
        # investigations: lookup by case_id and URL
        await db.investigations.create_index("case_id", unique=True)
        await db.investigations.create_index("url")
        await db.investigations.create_index("investigated_at")

        # products: dedup by product_id + source
        await db.products.create_index(
            [("product_id", ASCENDING), ("source", ASCENDING)],
            unique=True
        )
        await db.products.create_index("category_raw")

        # reviews: fast lookup by product_id and date
        await db.reviews.create_index("product_id")
        await db.reviews.create_index([("product_id", ASCENDING), ("date", DESCENDING)])
        await db.reviews.create_index([("body", TEXT)])  # full-text search

        # feedback: lookup by case_id
        await db.feedback.create_index("case_id")

        logger.info("Database indexes created.")
    except OperationFailure as e:
        logger.warning(f"Index creation warning (may already exist): {e}")


# ─── Investigation CRUD ───────────────────────────────────────────────────────

async def save_investigation(case_id: str, data: Dict[str, Any]) -> bool:
    db = get_db()
    try:
        data["case_id"] = case_id
        data["saved_at"] = datetime.utcnow()
        await db.investigations.insert_one(data)
        return True
    except DuplicateKeyError:
        await db.investigations.replace_one({"case_id": case_id}, data)
        return True
    except Exception as e:
        logger.error(f"save_investigation failed: {e}")
        return False


async def get_investigation(case_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = await db.investigations.find_one({"case_id": case_id}, {"_id": 0})
    return doc


async def get_recent_investigations(limit: int = 20) -> List[Dict[str, Any]]:
    db = get_db()
    cursor = db.investigations.find(
        {},
        {"case_id": 1, "product_title": 1, "verdict": 1, "investigated_at": 1, "_id": 0}
    ).sort("investigated_at", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ─── Product CRUD ─────────────────────────────────────────────────────────────

async def save_product(product_data: Dict[str, Any]) -> bool:
    db = get_db()
    try:
        product_data["updated_at"] = datetime.utcnow()
        await db.products.update_one(
            {"product_id": product_data["product_id"], "source": product_data["source"]},
            {"$set": product_data},
            upsert=True,
        )
        return True
    except Exception as e:
        logger.error(f"save_product failed: {e}")
        return False


async def get_product(product_id: str, source: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    return await db.products.find_one(
        {"product_id": product_id, "source": source}, {"_id": 0}
    )


# ─── Reviews CRUD ─────────────────────────────────────────────────────────────

async def save_reviews(product_id: str, reviews: List[Dict[str, Any]]) -> int:
    """Bulk upsert reviews. Returns count inserted."""
    if not reviews:
        return 0
    db = get_db()
    ops = []
    from pymongo import UpdateOne
    for r in reviews:
        r["product_id"] = product_id
        ops.append(UpdateOne(
            {"review_id": r["review_id"]},
            {"$set": r},
            upsert=True,
        ))
    try:
        result = await db.reviews.bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count
    except Exception as e:
        logger.error(f"save_reviews bulk_write failed: {e}")
        return 0


async def get_reviews(
    product_id: str,
    limit: int = 500,
    since_days: int = 180,
) -> List[Dict[str, Any]]:
    db = get_db()
    since = datetime.utcnow() - timedelta(days=since_days)
    cursor = db.reviews.find(
        {"product_id": product_id, "date": {"$gte": since}},
        {"_id": 0},
    ).sort("date", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


# ─── Feedback CRUD ────────────────────────────────────────────────────────────

async def save_feedback(
    case_id: str,
    user_verdict: str,
    system_verdict: str,
    helpful: bool,
    comment: str = "",
) -> bool:
    db = get_db()
    try:
        await db.feedback.insert_one({
            "case_id": case_id,
            "user_verdict": user_verdict,
            "system_verdict": system_verdict,
            "helpful": helpful,
            "comment": comment,
            "created_at": datetime.utcnow(),
        })
        return True
    except Exception as e:
        logger.error(f"save_feedback failed: {e}")
        return False


# ─── Analytics queries ────────────────────────────────────────────────────────

async def get_verdict_stats() -> Dict[str, Any]:
    """Aggregate verdict distribution across all investigations."""
    db = get_db()
    pipeline = [
        {"$group": {"_id": "$verdict", "count": {"$sum": 1}}},
        {"$sort": {"count": DESCENDING}},
    ]
    cursor = db.investigations.aggregate(pipeline)
    results = await cursor.to_list(length=10)
    return {r["_id"]: r["count"] for r in results}


async def get_category_stats() -> List[Dict[str, Any]]:
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "avg_confidence": {"$avg": "$confidence"},
        }},
        {"$sort": {"count": DESCENDING}},
    ]
    cursor = db.investigations.aggregate(pipeline)
    return await cursor.to_list(length=20)
