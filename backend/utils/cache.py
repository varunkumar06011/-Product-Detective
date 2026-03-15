"""
Product Detective — Redis Cache Utility
Async Redis cache using redis.asyncio.
"""

import json
import logging
from typing import Any, Optional
from urllib.parse import urlparse

import redis.asyncio as redis_async

from config.settings import settings

logger = logging.getLogger(__name__)

_redis: Any = None


async def init_cache():
    """Initialise the Redis connection pool."""
    global _redis
    try:
        parsed = urlparse(settings.REDIS_URL)
        host = parsed.hostname or "redis"
        port = parsed.port or 6379
        
        _redis = redis_async.Redis(
            host=host,
            port=port,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await _redis.ping()
        logger.info(f"✅ Redis connected: {host}:{port}")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}) — caching disabled.")
        _redis = None


async def get_cache(key: str) -> Optional[Any]:
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache GET failed for '{key}': {e}")
    return None


async def set_cache(key: str, value: Any, ttl: int = None) -> bool:
    if _redis is None:
        return False
    try:
        ttl = ttl or settings.CACHE_TTL
        await _redis.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as e:
        logger.warning(f"Cache SET failed for '{key}': {e}")
        return False


async def delete_cache(key: str) -> bool:
    if _redis is None:
        return False
    try:
        await _redis.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache DELETE failed for '{key}': {e}")
        return False


async def invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    if _redis is None:
        return 0
    try:
        keys = await _redis.keys(pattern)
        if keys:
            return await _redis.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache INVALIDATE failed for pattern '{pattern}': {e}")
        return 0
