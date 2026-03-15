from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from modules.recommendation_engine import RecommendationEngine
from utils.database import get_investigation

logger = logging.getLogger(__name__)
router = APIRouter()
rec_engine = RecommendationEngine()


class RecommendRequest(BaseModel):
    category: str
    product_price: float
    verdict: str
    current_score: float = 50.0
    user_budget: float = 0
    user_priority: str = "performance"


@router.post("/alternatives")
async def get_alternatives(req: RecommendRequest):
    report = rec_engine.recommend(
        category=req.category,
        product_price=req.product_price,
        verdict=req.verdict,
        current_score=req.current_score,
        user_budget=req.user_budget,
        user_priority=req.user_priority,
    )
    return {
        "found": report.found,
        "message": report.message,
        "alternatives": [
            {
                "name": a.name,
                "price": a.price,
                "score": a.score,
                "trust_score": a.trust_score,
                "avg_rating": a.avg_rating,
                "complaint_pct": a.complaint_pct,
                "key_advantages": a.key_advantages,
                "why_better": a.why_better,
            }
            for a in report.alternatives
        ],
    }


@router.get("/case/{case_id}")
async def get_case_alternatives(case_id: str):
    """Retrieve alternatives from a previously completed case."""
    inv = await get_investigation(case_id)
    if not inv:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {"case_id": case_id, "alternatives": inv.get("alternatives", [])}