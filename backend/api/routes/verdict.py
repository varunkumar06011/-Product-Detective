"""
Product Detective — Verdict API Route
Orchestrates the full investigation pipeline:
scrape → sentiment → complaints → trends → trust → specs → decision → recommend
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Dict, Any, List
import asyncio
import logging
from datetime import datetime

from modules.product_scraper import ProductScraper
from modules.sentiment_model import SentimentModel
from modules.complaint_detector import ComplaintDetector
from modules.complaint_trend_analyzer import ComplaintTrendAnalyzer
from modules.review_trust_model import ReviewTrustModel
from modules.category_classifier import SpecEvaluator
from modules.decision_engine import DecisionEngine
from modules.recommendation_engine import RecommendationEngine
from utils.database import get_db
from utils.cache import get_cache, set_cache
from utils.auth import get_current_user_optional, is_user_pro
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Module singletons
scraper             = ProductScraper()
sentiment_model     = SentimentModel()
complaint_detector  = ComplaintDetector()
trend_analyzer      = ComplaintTrendAnalyzer()
trust_model         = ReviewTrustModel()
spec_evaluator      = SpecEvaluator()
decision_engine     = DecisionEngine()
recommendation_engine = RecommendationEngine()


# ─── Request / Response models ────────────────────────────────────────────────

class InvestigationRequest(BaseModel):
    url: str
    budget: Optional[float] = 0
    purpose: Optional[str] = "daily"
    priority: Optional[str] = "performance"

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ClueCard(BaseModel):
    id: str
    title: str
    icon: str
    stamp: str       # "safe" | "warning" | "danger" | "neutral"
    tag: str
    preview: str
    detail: Dict[str, Any]


class InvestigationResponse(BaseModel):
    case_id: str
    status: str
    product_title: str
    product_price: float
    product_rating: float
    product_review_count: int
    category: str
    clue_cards: List[ClueCard]
    verdict: str
    confidence: int
    evidence: List[str]
    alternatives: List[Dict[str, Any]]
    investigated_at: str
    is_pro: bool = False
    paywall: Optional[Dict[str, Any]] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_product(
    req: InvestigationRequest,
    user=Depends(get_current_user_optional),
):
    """
    Full investigation pipeline. Returns all clue cards + final verdict.
    Results cached for 1 hour per URL.
    Free users see the verdict + a preview of evidence; full evidence &
    alternatives are unlocked for Pro users.
    """
    user_pro = is_user_pro(user)
    cache_key = f"investigation:{req.url}:{req.purpose}:{req.priority}:{user_pro}"

    # Cache check
    cached = await get_cache(cache_key)
    if cached:
        logger.info(f"Cache hit for {req.url}")
        return cached

    case_id = f"PD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    logger.info(f"[{case_id}] Starting investigation: {req.url}")

    try:
        # ── Stage 1: Scrape ────────────────────────────────────────────────
        product = await scraper.scrape(req.url)
        if product.error:
            raise HTTPException(status_code=422, detail=f"Scrape error: {product.error}")

        reviews_raw = [
            {
                "review_id": r.review_id,
                "body": r.body,
                "rating": r.rating,
                "date": r.date.isoformat(),
                "verified_purchase": r.verified_purchase,
                "title": r.title,
            }
            for r in product.reviews
        ]

        if len(reviews_raw) < 5:
            raise HTTPException(
                status_code=422,
                detail="Insufficient reviews found for analysis (minimum 5 required)."
            )

        # ── Stage 2: Sentiment ─────────────────────────────────────────────
        sentiment = sentiment_model.analyze_reviews(reviews_raw)
        sentiment_map = {r.review_id: r.label for r in sentiment.per_review}

        # ── Stage 3: Complaint detection ───────────────────────────────────
        complaints = complaint_detector.detect(
            reviews_raw,
            product_category=product.category_raw,
            sentiment_labels=sentiment_map,
        )

        # ── Stage 4: Trend analysis ────────────────────────────────────────
        trends = trend_analyzer.analyze(reviews_raw, complaints.clusters)

        # ── Stage 5: Trust scoring ─────────────────────────────────────────
        trust = trust_model.calculate(reviews_raw, sentiment_map)

        # ── Stage 6: Spec evaluation ───────────────────────────────────────
        category_eval = spec_evaluator.evaluate(
            product.title,
            product.specifications,
            user_purpose=req.purpose,
        )

        # ── Stage 7: Decision ──────────────────────────────────────────────
        decision = decision_engine.decide(
            sentiment_report=sentiment,
            complaint_report=complaints,
            trend_report=trends,
            trust_report=trust,
            category_eval=category_eval,
            user_budget=req.budget,
            product_price=product.price,
            user_purpose=req.purpose,
            user_priority=req.priority,
        )

        # ── Stage 8: Recommendations ───────────────────────────────────────
        recs = recommendation_engine.recommend(
            category=category_eval.detected_category,
            product_price=product.price,
            verdict=decision.verdict.value,
            current_score=category_eval.overall_spec_score,
            user_budget=req.budget,
            user_priority=req.priority,
        )

        # ── Build clue cards ───────────────────────────────────────────────
        clue_cards = _build_clue_cards(sentiment, complaints, trends, trust, category_eval)

        # ── Build evidence strings ─────────────────────────────────────────
        evidence = [e.text for e in decision.evidence]
        if decision.budget_note:
            evidence.append(decision.budget_note)

        # ── Build alternatives ─────────────────────────────────────────────
        alternatives = [
            {
                "rank": f"{i+1:02d}",
                "name": a.name,
                "price": a.price,
                "score": a.score,
                "reasons": a.key_advantages,
                "why_better": a.why_better,
                "trust_score": a.trust_score,
                "avg_rating": a.avg_rating,
            }
            for i, a in enumerate(recs.alternatives)
        ]

        result = InvestigationResponse(
            case_id=case_id,
            status="complete",
            product_title=product.title,
            product_price=product.price,
            product_rating=product.rating,
            product_review_count=product.review_count,
            category=category_eval.detected_category,
            clue_cards=[c.model_dump() for c in clue_cards],
            verdict=decision.verdict.value,
            confidence=decision.confidence,
            evidence=evidence,
            alternatives=alternatives,
            investigated_at=datetime.utcnow().isoformat(),
            is_pro=user_pro,
        )

        # ── Paywall: truncate detailed results for free users ──────────────
        if not user_pro:
            preview_n = settings.FREE_EVIDENCE_PREVIEW
            full_evidence_count = len(evidence)
            full_alternatives_count = len(alternatives)
            full_clue_count = len(clue_cards)

            # Truncate evidence to preview count
            result.evidence = evidence[:preview_n]
            # Hide alternatives entirely
            result.alternatives = []
            # Show only the first clue card (sentiment) as a teaser;
            # lock the rest (complaints, trends, trust, specs)
            result.clue_cards = [c.model_dump() for c in clue_cards[:1]]
            result.paywall = {
                "locked": True,
                "message": (
                    "You're seeing a preview. Unlock the full evidence, "
                    "complaint analysis, trust score, and better alternatives with Pro."
                ),
                "hidden_evidence_count": max(0, full_evidence_count - preview_n),
                "hidden_alternatives_count": full_alternatives_count,
                "hidden_clue_cards_count": max(0, full_clue_count - 1),
            }

        await set_cache(cache_key, result.model_dump())
        logger.info(f"[{case_id}] Investigation complete — verdict: {decision.verdict.value}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        # User-facing errors (bad URL, unsupported platform, image URL, etc.)
        logger.warning(f"[{case_id}] Invalid input: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"[{case_id}] Investigation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Investigation error: {str(e)}")


@router.get("/status/{case_id}")
async def get_case_status(case_id: str):
    """Check case status (for async long-running investigations)."""
    return {"case_id": case_id, "status": "complete"}


# ─── Clue card builder ────────────────────────────────────────────────────────

def _build_clue_cards(
    sentiment, complaints, trends, trust, category_eval
) -> List[ClueCard]:
    cards = []

    # 1. Sentiment card
    neg = sentiment.negative_pct
    stamp = "danger" if neg > 30 else "warning" if neg > 18 else "safe"
    cards.append(ClueCard(
        id="sentiment",
        title="Review Sentiment",
        icon="💬",
        stamp=stamp,
        tag="RED FLAG" if neg > 30 else "MIXED SIGNALS" if neg > 18 else "POSITIVE",
        preview=f"{sentiment.positive_pct:.0f}% positive · {neg:.0f}% negative",
        detail={
            "label": f"SENTIMENT ANALYSIS — {complaints.total_reviews} REVIEWS",
            "bars": [
                {"label": "Positive", "pct": int(sentiment.positive_pct), "type": "good"},
                {"label": "Neutral",  "pct": int(sentiment.neutral_pct),  "type": "warn"},
                {"label": "Negative", "pct": int(sentiment.negative_pct), "type": "bad"},
            ],
            "tags": sentiment.top_positive_phrases[:4] + sentiment.top_negative_phrases[:4],
            "tagTypes": ["positive"] * len(sentiment.top_positive_phrases[:4]) +
                        ["complaint"] * len(sentiment.top_negative_phrases[:4]),
            "alert": {
                "type": "danger" if neg > 30 else "warning" if neg > 18 else "success",
                "text": (f"{neg:.0f}% negative reviews is above the category average of 18%."
                         if neg > 18 else "Sentiment looks healthy for this category."),
            }
        }
    ))

    # 2. Complaints card
    has_critical = any(c.severity == "critical" for c in complaints.clusters)
    stamp2 = "danger" if has_critical else "warning" if complaints.clusters else "safe"
    cards.append(ClueCard(
        id="complaints",
        title="Major Complaints",
        icon="⚠️",
        stamp=stamp2,
        tag="RED FLAG" if has_critical else "MINOR ISSUES" if complaints.clusters else "CLEAN",
        preview=(complaints.clusters[0].label if complaints.clusters
                 else "No major complaints detected"),
        detail={
            "label": "TOP COMPLAINT CLUSTERS",
            "bars": [
                {
                    "label": c.label[:25],
                    "pct": int(c.total_pct),
                    "type": "bad" if c.severity == "critical" else "warn",
                }
                for c in complaints.clusters[:6]
            ],
            "alert": {
                "type": "danger" if has_critical else "warning",
                "text": (
                    f"{complaints.clusters[0].label} reported by "
                    f"{complaints.clusters[0].total_pct:.0f}% of users."
                    if complaints.clusters else "No significant complaints found."
                ),
            }
        }
    ))

    # 3. Trend card
    rising = [s for s in trends.signals if s.is_rising and s.significance in ("high","medium")]
    stamp3 = "danger" if rising else "safe"
    cards.append(ClueCard(
        id="timeline",
        title="Complaint Timeline",
        icon="📈",
        stamp=stamp3,
        tag="RISING TREND" if rising else "STABLE",
        preview=(f"{rising[0].label} complaints rising" if rising
                 else "Complaint patterns stable"),
        detail={
            "label": "COMPLAINT TREND — LAST 6 MONTHS",
            "timeline": [
                {
                    "date": p.month,
                    "text": rising[0].label if rising else "All complaints",
                    "pct": f"{p.complaint_pct:.1f}%",
                    "type": "rise" if rising else "stable",
                }
                for p in (rising[0].monthly_data if rising else [])[:6]
            ],
            "alert": {
                "type": "danger" if rising else "success",
                "text": trends.summary,
            }
        }
    ))

    # 4. Trust card
    t_score = trust.score
    stamp4 = "safe" if t_score >= 80 else "warning" if t_score >= 60 else "danger"
    cards.append(ClueCard(
        id="trust",
        title="Review Trust Score",
        icon="🛡️",
        stamp=stamp4,
        tag="AUTHENTIC" if t_score >= 80 else "SUSPICIOUS" if t_score < 60 else "MIXED",
        preview=f"{t_score}/100 — {trust.grade} grade",
        detail={
            "label": "REVIEW AUTHENTICITY ANALYSIS",
            "score": {"value": t_score, "type": stamp4, "label": "/100"},
            "bars": [
                {
                    "label": s.signal_name.replace("_", " ").title()[:25],
                    "pct": int(s.value),
                    "type": "bad" if s.severity == "high" else
                            "warn" if s.severity == "medium" else "good",
                }
                for s in trust.signals[:5]
            ],
            "alert": {
                "type": stamp4,
                "text": trust.summary,
            }
        }
    ))

    # 5. Spec card
    if category_eval.spec_scores:
        overall = category_eval.overall_spec_score
        stamp5 = "safe" if overall >= 70 else "warning" if overall >= 50 else "danger"
        cards.append(ClueCard(
            id="specs",
            title="Spec Match Clue",
            icon="🔬",
            stamp=stamp5,
            tag="WELL MATCHED" if overall >= 70 else "ADEQUATE" if overall >= 50 else "WEAK",
            preview=f"Overall spec score {overall:.0f}/100",
            detail={
                "label": f"{category_eval.detected_category.upper()} SPEC EVALUATION",
                "bars": [
                    {
                        "label": s.display_name[:25],
                        "pct": int(s.score),
                        "type": "good" if s.score >= 70 else "warn" if s.score >= 50 else "bad",
                    }
                    for s in category_eval.spec_scores
                ],
                "alert": {
                    "type": stamp5,
                    "text": (
                        f"Weaknesses: {', '.join(category_eval.weaknesses[:3])}"
                        if category_eval.weaknesses
                        else f"Strengths: {', '.join(category_eval.strengths[:3])}"
                    ),
                }
            }
        ))

    return cards
