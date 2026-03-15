"""
Product Detective — Recommendation Engine
When a product gets WAIT or AVOID, finds better alternatives.
Uses a category-specific scoring model + product database lookup.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class Alternative:
    name: str
    price: float
    category: str
    score: float          # 0–100 composite score
    key_advantages: List[str]
    trust_score: int
    avg_rating: float
    complaint_pct: float
    why_better: str


@dataclass
class RecommendationReport:
    found: bool
    alternatives: List[Alternative]
    message: str


# ─── Static product knowledge base (production: swap with MongoDB + vector DB) ─────

PRODUCT_DATABASE = {
    "laptop": [
        {
            "name": "ASUS ROG Strix G15 (2024)",
            "price": 89990,
            "score": 84,
            "trust_score": 88,
            "avg_rating": 4.3,
            "complaint_pct": 12,
            "advantages": [
                "Vapor chamber cooling — only 12% overheating complaints",
                "RTX 4070 — stronger GPU at similar price",
                "Stable reviews over 12 months — no defect spikes",
                "MUX switch for direct GPU output",
            ],
        },
        {
            "name": "Lenovo Legion 5 Pro (2024)",
            "price": 92000,
            "score": 88,
            "trust_score": 91,
            "avg_rating": 4.5,
            "complaint_pct": 9,
            "advantages": [
                "Best-in-class thermals for gaming laptops",
                "90Wh battery — 50% more capacity than most competitors",
                "Trust score 91/100 — genuinely loved by users",
                "165Hz QHD display",
            ],
        },
        {
            "name": "MSI Katana GF66",
            "price": 69990,
            "score": 72,
            "trust_score": 78,
            "avg_rating": 4.1,
            "complaint_pct": 18,
            "advantages": [
                "Budget-friendly at ₹20k less",
                "Consistent performance review history",
                "Good price-to-GPU ratio",
            ],
        },
        {
            "name": "Acer Nitro 5 (2024)",
            "price": 65000,
            "score": 68,
            "trust_score": 76,
            "avg_rating": 3.9,
            "complaint_pct": 20,
            "advantages": [
                "Lowest price in class",
                "Upgradeable RAM and storage",
                "Solid build for the price point",
            ],
        },
    ],
    "phone": [
        {
            "name": "Samsung Galaxy S23 FE",
            "price": 34999,
            "score": 82,
            "trust_score": 85,
            "avg_rating": 4.3,
            "complaint_pct": 11,
            "advantages": [
                "Snapdragon 8 Gen 1 — flagship-class performance",
                "4 years of OS updates",
                "Superior camera system vs A54",
            ],
        },
        {
            "name": "Nothing Phone 2a",
            "price": 24999,
            "score": 79,
            "trust_score": 84,
            "avg_rating": 4.2,
            "complaint_pct": 14,
            "advantages": [
                "Dimensity 7200 Pro — fast and efficient",
                "Unique design with Glyph interface",
                "45W charging — much faster",
            ],
        },
    ],
    "earbuds": [
        {
            "name": "Noise Buds VS104",
            "price": 1499,
            "score": 77,
            "trust_score": 82,
            "avg_rating": 4.1,
            "complaint_pct": 11,
            "advantages": [
                "Same price bracket as reviewed product",
                "Only 11% negative reviews vs 41%",
                "Stable quality history over 8 months",
            ],
        },
        {
            "name": "Realme Buds T100",
            "price": 1499,
            "score": 75,
            "trust_score": 82,
            "avg_rating": 4.0,
            "complaint_pct": 13,
            "advantages": [
                "Far better durability track record",
                "Good mic quality for calls",
                "Trust score 82/100",
            ],
        },
        {
            "name": "JBL Tune Flex",
            "price": 3999,
            "score": 85,
            "trust_score": 88,
            "avg_rating": 4.4,
            "complaint_pct": 8,
            "advantages": [
                "JBL sound quality at entry-premium price",
                "IP54 water resistance",
                "Only 8% complaint rate — best in class reliability",
            ],
        },
    ],
}


class RecommendationEngine:
    """
    Finds better alternatives when a product gets WAIT or AVOID.
    Filters by:
    1. Same category
    2. Price within ±30% of original
    3. Higher composite score
    """

    PRICE_TOLERANCE = 0.35  # ±35%
    MAX_ALTERNATIVES = 3

    def recommend(
        self,
        category: str,
        product_price: float,
        verdict: str,               # "BUY" | "WAIT" | "AVOID"
        current_score: float,       # 0–100
        user_budget: float = 0,
        user_priority: str = "performance",
    ) -> RecommendationReport:

        if verdict == "BUY":
            return RecommendationReport(
                found=False,
                alternatives=[],
                message="Current product is recommended — no alternatives needed.",
            )

        cat_key = self._map_category(category)
        candidates = PRODUCT_DATABASE.get(cat_key, [])

        if not candidates:
            return RecommendationReport(
                found=False,
                alternatives=[],
                message=f"No alternatives in database for category: {category}",
            )

        budget = max(user_budget, product_price) if user_budget > 0 else product_price
        filtered = self._filter_candidates(candidates, budget, current_score)
        ranked = self._rank_candidates(filtered, user_priority)[:self.MAX_ALTERNATIVES]

        if not ranked:
            return RecommendationReport(
                found=False,
                alternatives=[],
                message="No clearly better alternatives found in your price range.",
            )

        alternatives = [
            Alternative(
                name=c["name"],
                price=c["price"],
                category=category,
                score=c["score"],
                key_advantages=c["advantages"][:3],
                trust_score=c["trust_score"],
                avg_rating=c["avg_rating"],
                complaint_pct=c["complaint_pct"],
                why_better=self._why_better(c, current_score, verdict),
            )
            for c in ranked
        ]

        return RecommendationReport(
            found=True,
            alternatives=alternatives,
            message=f"Found {len(alternatives)} better option(s) in your price range.",
        )

    def _filter_candidates(
        self,
        candidates: List[Dict],
        budget: float,
        current_score: float,
    ) -> List[Dict]:
        low  = budget * (1 - self.PRICE_TOLERANCE)
        high = budget * (1 + self.PRICE_TOLERANCE)
        return [
            c for c in candidates
            if low <= c["price"] <= high
            and c["score"] > current_score
        ]

    def _rank_candidates(
        self,
        candidates: List[Dict],
        priority: str,
    ) -> List[Dict]:
        def score_key(c):
            base = c["score"]
            if priority == "price":
                # Penalise more expensive options
                return base - c["price"] / 10000
            elif priority == "durability":
                # Trust score matters more
                return base * 0.6 + c["trust_score"] * 0.4
            else:  # performance default
                return base

        return sorted(candidates, key=score_key, reverse=True)

    def _why_better(
        self,
        candidate: Dict,
        current_score: float,
        verdict: str,
    ) -> str:
        score_diff = candidate["score"] - current_score
        if verdict == "AVOID" and candidate["complaint_pct"] < 15:
            return f"{score_diff:.0f} points better overall — far fewer reliability issues"
        elif verdict == "WAIT":
            return f"Stronger score (+{score_diff:.0f}) with better long-term reliability data"
        return f"Better value with {score_diff:.0f} point higher composite score"

    def _map_category(self, raw: str) -> str:
        raw_lower = raw.lower()
        if any(w in raw_lower for w in ["laptop", "notebook"]):
            return "laptop"
        if any(w in raw_lower for w in ["phone", "smartphone", "mobile"]):
            return "phone"
        if any(w in raw_lower for w in ["earbud", "earphone", "headphone", "tws"]):
            return "earbuds"
        return raw_lower
