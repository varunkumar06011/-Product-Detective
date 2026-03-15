"""
Product Detective — Decision Engine
Combines all analysis signals into a final BUY / WAIT / AVOID verdict
with confidence score and explainable reasoning.

Signal weights (total = 1.0):
  - Sentiment score:        0.20
  - Complaint severity:     0.25
  - Complaint trend:        0.20
  - Review trust:           0.15
  - Spec match:             0.15
  - Budget match:           0.05
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    BUY  = "BUY"
    WAIT = "WAIT"
    AVOID = "AVOID"


@dataclass
class EvidencePoint:
    text: str
    signal: str         # which signal generated this
    impact: str         # "positive" | "negative" | "neutral"
    weight: float


@dataclass
class DecisionResult:
    verdict: Verdict
    confidence: int         # 0–100
    composite_score: float  # 0.0–1.0 (higher = better product)
    evidence: List[EvidencePoint]
    summary: str
    budget_note: Optional[str] = None
    recommendation_note: Optional[str] = None


# Signal weights
WEIGHTS = {
    "sentiment":        0.20,
    "complaint":        0.25,
    "trend":            0.20,
    "trust":            0.15,
    "specs":            0.15,
    "budget":           0.05,
}

# Thresholds
THRESHOLDS = {
    "buy":  0.68,
    "wait": 0.44,
}


class DecisionEngine:
    """
    Aggregates all analysis module outputs into a final investment decision.
    Uses a weighted composite score normalised 0–1.
    Score >= 0.68 → BUY
    Score 0.44–0.68 → WAIT
    Score < 0.44  → AVOID
    """

    def decide(
        self,
        sentiment_report,       # SentimentReport
        complaint_report,       # ComplaintReport
        trend_report,           # TrendReport
        trust_report,           # TrustReport
        category_eval,          # CategoryEvaluation
        user_budget: float = 0,
        product_price: float = 0,
        user_purpose: str = "daily",
        user_priority: str = "performance",
    ) -> DecisionResult:

        signals: Dict[str, float] = {}
        evidence: List[EvidencePoint] = []

        # ── 1. Sentiment score ──────────────────────────────────────────────
        if sentiment_report:
            pos = sentiment_report.positive_pct / 100
            neg = sentiment_report.negative_pct / 100
            # Net sentiment normalised to 0–1
            sentiment_score = max(0, min(1, pos - neg * 0.5 + 0.5))
            signals["sentiment"] = sentiment_score

            if neg > 0.30:
                evidence.append(EvidencePoint(
                    f"{sentiment_report.negative_pct:.0f}% of reviews are negative "
                    f"(category avg ~18%)",
                    "sentiment", "negative", WEIGHTS["sentiment"]
                ))
            elif pos > 0.65:
                evidence.append(EvidencePoint(
                    f"{sentiment_report.positive_pct:.0f}% positive reviews — "
                    f"strong community approval",
                    "sentiment", "positive", WEIGHTS["sentiment"]
                ))

        # ── 2. Complaint severity score ─────────────────────────────────────
        if complaint_report:
            critical = [c for c in complaint_report.clusters if c.severity == "critical"]
            moderate = [c for c in complaint_report.clusters if c.severity == "moderate"]
            complaint_score = max(0, 1.0 - len(critical) * 0.3 - len(moderate) * 0.1)
            signals["complaint"] = complaint_score

            for c in critical:
                evidence.append(EvidencePoint(
                    f"{c.label}: {c.total_pct:.0f}% of users report this — "
                    f"critical issue",
                    "complaint", "negative", WEIGHTS["complaint"]
                ))
            if not critical and not moderate:
                evidence.append(EvidencePoint(
                    "No critical complaint patterns detected",
                    "complaint", "positive", WEIGHTS["complaint"]
                ))

        # ── 3. Trend score ──────────────────────────────────────────────────
        if trend_report:
            rising_high = [s for s in trend_report.signals
                           if s.is_rising and s.significance == "high"]
            rising_med  = [s for s in trend_report.signals
                           if s.is_rising and s.significance == "medium"]
            trend_score = max(0, 1.0 - len(rising_high) * 0.35 - len(rising_med) * 0.15)
            signals["trend"] = trend_score

            for s in rising_high[:2]:
                evidence.append(EvidencePoint(
                    f"{s.label} complaints rose "
                    f"{s.start_pct:.0f}% → {s.end_pct:.0f}% in 6 months",
                    "trend", "negative", WEIGHTS["trend"]
                ))
            if not rising_high and not rising_med:
                evidence.append(EvidencePoint(
                    "Complaint trends stable — no emerging defect patterns",
                    "trend", "positive", WEIGHTS["trend"]
                ))

        # ── 4. Trust score ───────────────────────────────────────────────────
        if trust_report:
            trust_score = trust_report.score / 100
            signals["trust"] = trust_score

            if trust_report.score < 60:
                evidence.append(EvidencePoint(
                    f"Review trust score {trust_report.score}/100 — "
                    f"possible manipulation detected",
                    "trust", "negative", WEIGHTS["trust"]
                ))
            elif trust_report.score >= 80:
                evidence.append(EvidencePoint(
                    f"Review trust score {trust_report.score}/100 — "
                    f"reviews appear authentic",
                    "trust", "positive", WEIGHTS["trust"]
                ))

        # ── 5. Spec score ───────────────────────────────────────────────────
        if category_eval:
            spec_score = category_eval.overall_spec_score / 100
            signals["specs"] = spec_score

            if category_eval.weaknesses:
                evidence.append(EvidencePoint(
                    f"Spec weaknesses: {', '.join(category_eval.weaknesses[:3])}",
                    "specs", "negative", WEIGHTS["specs"]
                ))
            if category_eval.strengths:
                evidence.append(EvidencePoint(
                    f"Spec strengths: {', '.join(category_eval.strengths[:3])}",
                    "specs", "positive", WEIGHTS["specs"]
                ))

        # ── 6. Budget score ──────────────────────────────────────────────────
        budget_note = None
        if user_budget > 0 and product_price > 0:
            ratio = product_price / user_budget
            if ratio <= 0.85:
                budget_score = 1.0
                budget_note = f"Product (₹{product_price:,.0f}) is within your budget (₹{user_budget:,.0f})"
            elif ratio <= 1.0:
                budget_score = 0.8
                budget_note = f"Tight fit within budget"
            elif ratio <= 1.15:
                budget_score = 0.5
                budget_note = f"Slightly over budget by ₹{product_price - user_budget:,.0f}"
            else:
                budget_score = 0.2
                budget_note = f"Over budget by ₹{product_price - user_budget:,.0f} ({(ratio-1)*100:.0f}%)"
            signals["budget"] = budget_score

        # ── Composite score ──────────────────────────────────────────────────
        total_weight = sum(WEIGHTS[k] for k in signals)
        composite = sum(signals[k] * WEIGHTS[k] for k in signals) / max(total_weight, 0.01)

        # ── Verdict ──────────────────────────────────────────────────────────
        if composite >= THRESHOLDS["buy"]:
            verdict = Verdict.BUY
        elif composite >= THRESHOLDS["wait"]:
            verdict = Verdict.WAIT
        else:
            verdict = Verdict.AVOID

        # Override: if trust is very low, cap at WAIT
        if trust_report and trust_report.score < 45 and verdict == Verdict.BUY:
            verdict = Verdict.WAIT

        # Override: critical trend + critical complaint → AVOID
        if (trend_report and trend_report.has_critical_trend and
                complaint_report and any(c.severity == "critical" for c in complaint_report.clusters)):
            if verdict == Verdict.BUY:
                verdict = Verdict.WAIT

        # Confidence: how far from the nearest threshold
        if verdict == Verdict.BUY:
            confidence = int(min(99, 70 + (composite - THRESHOLDS["buy"]) * 150))
        elif verdict == Verdict.WAIT:
            dist = min(
                abs(composite - THRESHOLDS["buy"]),
                abs(composite - THRESHOLDS["wait"])
            )
            confidence = int(min(99, 50 + dist * 100))
        else:
            confidence = int(min(99, 70 + (THRESHOLDS["wait"] - composite) * 150))

        summary = self._build_summary(verdict, composite, evidence)

        return DecisionResult(
            verdict=verdict,
            confidence=confidence,
            composite_score=round(composite, 3),
            evidence=sorted(evidence, key=lambda e: e.weight, reverse=True),
            summary=summary,
            budget_note=budget_note,
        )

    def _build_summary(
        self,
        verdict: Verdict,
        score: float,
        evidence: List[EvidencePoint],
    ) -> str:
        neg_points = [e.text for e in evidence if e.impact == "negative"][:2]
        pos_points = [e.text for e in evidence if e.impact == "positive"][:2]

        if verdict == Verdict.BUY:
            return (
                f"Investigation complete — this product is worth buying. "
                f"Key strengths: {'; '.join(pos_points)}."
            )
        elif verdict == Verdict.WAIT:
            if neg_points:
                return (
                    f"Hold off for now. Concerns: {'; '.join(neg_points)}. "
                    f"Consider alternatives or wait for a price drop/fix."
                )
            return "Mixed signals — check alternatives before committing."
        else:
            return (
                f"Avoid this product. Critical issues: {'; '.join(neg_points)}. "
                f"Your money is better spent elsewhere."
            )
