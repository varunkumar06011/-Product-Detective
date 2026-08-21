from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from utils.database import get_db, get_verdict_stats, get_category_stats

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check — returns app status."""
    db_ok = True
    try:
        db = get_db()
        await db.command("ping")
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "Product Detective API",
        "version": "1.0.0",
        "database": "connected" if db_ok else "unavailable",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/stats")
async def get_stats():
    """Aggregate statistics across all investigations."""
    try:
        verdicts = await get_verdict_stats()
        categories = await get_category_stats()
        return {
            "verdict_distribution": verdicts,
            "top_categories": categories[:5],
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Stats endpoint failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")