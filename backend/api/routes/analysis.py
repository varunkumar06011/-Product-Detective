from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from modules.sentiment_model import SentimentModel
from modules.complaint_detector import ComplaintDetector
from modules.complaint_trend_analyzer import ComplaintTrendAnalyzer
from modules.review_trust_model import ReviewTrustModel
from modules.category_classifier import SpecEvaluator

logger = logging.getLogger(__name__)
router = APIRouter()

sentiment_model    = SentimentModel()
complaint_detector = ComplaintDetector()
trend_analyzer     = ComplaintTrendAnalyzer()
trust_model        = ReviewTrustModel()
spec_evaluator     = SpecEvaluator()


class ReviewInput(BaseModel):
    review_id: str
    body: str
    rating: float = 3.0
    date: Optional[str] = None
    verified_purchase: bool = False


class SentimentRequest(BaseModel):
    reviews: List[ReviewInput]


class ComplaintRequest(BaseModel):
    reviews: List[ReviewInput]
    product_category: str = "generic"
    sentiment_labels: Optional[Dict[str, str]] = None


class TrustRequest(BaseModel):
    reviews: List[ReviewInput]
    sentiment_labels: Optional[Dict[str, str]] = None


class SpecRequest(BaseModel):
    product_title: str
    specifications: Dict[str, str]
    user_purpose: str = "daily"


@router.post("/sentiment")
async def analyze_sentiment(req: SentimentRequest):
    """Run sentiment analysis on a batch of reviews."""
    raw = [r.model_dump() for r in req.reviews]
    report = sentiment_model.analyze_reviews(raw)
    return {
        "positive_pct": report.positive_pct,
        "neutral_pct": report.neutral_pct,
        "negative_pct": report.negative_pct,
        "avg_score": report.avg_score,
        "top_positive_phrases": report.top_positive_phrases,
        "top_negative_phrases": report.top_negative_phrases,
        "per_review": [
            {"review_id": r.review_id, "label": r.label, "confidence": r.confidence}
            for r in report.per_review
        ],
    }


@router.post("/complaints")
async def analyze_complaints(req: ComplaintRequest):
    """Detect complaint clusters from negative reviews."""
    raw = [r.model_dump() for r in req.reviews]
    report = complaint_detector.detect(
        raw,
        product_category=req.product_category,
        sentiment_labels=req.sentiment_labels,
    )
    return {
        "total_reviews": report.total_reviews,
        "total_negative": report.total_negative,
        "clusters": [
            {
                "category": c.category,
                "label": c.label,
                "frequency_pct": c.frequency_pct,
                "total_pct": c.total_pct,
                "severity": c.severity,
                "keywords": c.keywords,
                "examples": c.examples,
            }
            for c in report.clusters
        ],
    }


@router.post("/trust")
async def analyze_trust(req: TrustRequest):
    """Calculate review trust / authenticity score."""
    raw = [r.model_dump() for r in req.reviews]
    report = trust_model.calculate(raw, req.sentiment_labels or {})
    return {
        "score": report.score,
        "grade": report.grade,
        "adjusted_rating": report.adjusted_rating,
        "verified_pct": report.verified_pct,
        "summary": report.summary,
        "signals": [
            {
                "name": s.signal_name,
                "value": s.value,
                "penalty": s.penalty,
                "description": s.description,
                "severity": s.severity,
            }
            for s in report.signals
        ],
    }


@router.post("/specs")
async def evaluate_specs(req: SpecRequest):
    """Evaluate product specs for its detected category."""
    eval_result = spec_evaluator.evaluate(
        req.product_title,
        req.specifications,
        req.user_purpose,
    )
    return {
        "detected_category": eval_result.detected_category,
        "category_confidence": eval_result.category_confidence,
        "overall_score": eval_result.overall_spec_score,
        "strengths": eval_result.strengths,
        "weaknesses": eval_result.weaknesses,
        "spec_scores": [
            {
                "attribute": s.attribute,
                "display_name": s.display_name,
                "raw_value": s.raw_value,
                "score": s.score,
                "weight": s.weight,
                "note": s.note,
            }
            for s in eval_result.spec_scores
        ],
    }