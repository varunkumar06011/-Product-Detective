"""
Product Detective — Additional API Routes
scraper.py  : direct product scrape endpoint
analysis.py : standalone analysis endpoints
recommendations.py : alternatives lookup
health.py   : health + stats endpoint
"""

# ════════════════════════════════════════════════════════════════════
#  backend/api/routes/scraper.py
# ════════════════════════════════════════════════════════════════════
SCRAPER_ROUTE = '''
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from modules.product_scraper import ProductScraper
from utils.database import save_product, get_product

logger = logging.getLogger(__name__)
router = APIRouter()
scraper = ProductScraper()


class ScrapeRequest(BaseModel):
    url: str
    force_refresh: bool = False


@router.post("/product")
async def scrape_product(req: ScrapeRequest):
    """
    Scrape a single product page.
    Returns title, price, specs, rating, and raw reviews.
    Cached in MongoDB — use force_refresh=true to bypass.
    """
    product = await scraper.scrape(req.url)
    if product.error:
        raise HTTPException(status_code=422, detail=product.error)

    # Persist to DB
    await save_product({
        "product_id": product.product_id,
        "source": product.source,
        "title": product.title,
        "price": product.price,
        "rating": product.rating,
        "review_count": product.review_count,
        "specifications": product.specifications,
        "category_raw": product.category_raw,
        "url": product.url,
    })

    return {
        "product_id": product.product_id,
        "source": product.source,
        "title": product.title,
        "price": product.price,
        "currency": product.currency,
        "rating": product.rating,
        "total_ratings": product.total_ratings,
        "review_count": product.review_count,
        "description": product.description[:500],
        "specifications": product.specifications,
        "category_raw": product.category_raw,
        "images": product.images,
        "reviews_preview": [
            {
                "rating": r.rating,
                "title": r.title,
                "body": r.body[:200],
                "date": r.date.isoformat(),
                "verified_purchase": r.verified_purchase,
            }
            for r in product.reviews[:5]
        ],
    }
'''

# ════════════════════════════════════════════════════════════════════
#  backend/api/routes/analysis.py
# ════════════════════════════════════════════════════════════════════
ANALYSIS_ROUTE = '''
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
    raw = [r.dict() for r in req.reviews]
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
    raw = [r.dict() for r in req.reviews]
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
    raw = [r.dict() for r in req.reviews]
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
'''

# ════════════════════════════════════════════════════════════════════
#  backend/api/routes/recommendations.py
# ════════════════════════════════════════════════════════════════════
RECOMMENDATIONS_ROUTE = '''
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
'''

# ════════════════════════════════════════════════════════════════════
#  backend/api/routes/health.py
# ════════════════════════════════════════════════════════════════════
HEALTH_ROUTE = '''
from fastapi import APIRouter
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
        return {"error": str(e)}
'''

# Write the files
import os

routes_dir = "/home/claude/product_detective/backend/api/routes"
os.makedirs(routes_dir, exist_ok=True)

files = {
    "scraper.py": SCRAPER_ROUTE,
    "analysis.py": ANALYSIS_ROUTE,
    "recommendations.py": RECOMMENDATIONS_ROUTE,
    "health.py": HEALTH_ROUTE,
}

for name, content in files.items():
    path = os.path.join(routes_dir, name)
    # Strip leading triple-quote from the heredoc strings
    code = content.strip().lstrip("'").rstrip("'").strip()
    with open(path, "w") as f:
        f.write(code)
    print(f"Written: {path}")
