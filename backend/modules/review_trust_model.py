"""
Product Detective — Review Trust Model
Calculates a 0–100 review authenticity score by detecting:
  - Duplicate / near-duplicate reviews
  - Rating vs text sentiment mismatch
  - Sudden review spikes (burst patterns)
  - Generic, low-information reviews
  - Verified purchase ratio
"""

import logging
import re
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict

import numpy as np
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class TrustSignal:
    signal_name: str
    value: float       # raw metric
    penalty: float     # score penalty applied (0–25)
    description: str
    severity: str      # "high" | "medium" | "low"


@dataclass
class TrustReport:
    score: int                  # 0–100
    grade: str                  # A / B / C / D / F
    signals: List[TrustSignal]
    adjusted_rating: float      # estimated real rating
    verified_pct: float
    summary: str


class ReviewTrustModel:
    """
    Scores review trustworthiness. Each signal contributes a penalty.
    Base score is 100; penalties reduce it.

    Weights:
      - Duplicate reviews:          up to 20 pts
      - Rating-sentiment mismatch:  up to 15 pts
      - Burst / spike detection:    up to 20 pts
      - Generic reviews:            up to 15 pts
      - Unverified purchase ratio:  up to 15 pts
      - Length distribution:        up to 10 pts (very short = suspicious)
    """

    # Thresholds
    DUPLICATE_SIMILARITY = 0.85       # SequenceMatcher ratio
    BURST_WINDOW_DAYS = 7
    BURST_THRESHOLD = 0.20            # 20% of reviews in one week = suspicious
    GENERIC_MAX_LENGTH = 30           # words
    GENERIC_RATIO_THRESHOLD = 0.25    # 25%+ very short reviews
    MISMATCH_THRESHOLD = 0.25         # 25%+ mismatched = suspicious

    def calculate(
        self,
        reviews: List[Dict[str, Any]],  # {"review_id","body","rating","date","verified_purchase"}
        sentiment_labels: Dict[str, str] = None,  # review_id → "positive"|"neutral"|"negative"
    ) -> TrustReport:

        if len(reviews) < 5:
            return TrustReport(50, "C", [], 0.0, 0.0, "Too few reviews to assess trust.")

        signals = []
        base_score = 100

        # 1. Duplicate detection
        dup_signal = self._check_duplicates(reviews)
        signals.append(dup_signal)
        base_score -= dup_signal.penalty

        # 2. Rating-sentiment mismatch
        if sentiment_labels:
            mismatch_signal = self._check_mismatch(reviews, sentiment_labels)
            signals.append(mismatch_signal)
            base_score -= mismatch_signal.penalty

        # 3. Burst detection
        burst_signal = self._check_burst(reviews)
        signals.append(burst_signal)
        base_score -= burst_signal.penalty

        # 4. Generic review ratio
        generic_signal = self._check_generic(reviews)
        signals.append(generic_signal)
        base_score -= generic_signal.penalty

        # 5. Verified purchase ratio
        verified_signal = self._check_verified(reviews)
        signals.append(verified_signal)
        base_score -= verified_signal.penalty
        verified_pct = float(verified_signal.value)

        score = max(0, min(100, int(base_score)))
        grade = self._score_to_grade(score)
        adjusted_rating = self._adjusted_rating(reviews, signals)
        summary = self._build_summary(score, signals)

        return TrustReport(
            score=score,
            grade=grade,
            signals=signals,
            adjusted_rating=adjusted_rating,
            verified_pct=verified_pct,
            summary=summary,
        )

    # ─── Signal 1: Duplicate detection ────────────────────────────────────────

    def _check_duplicates(self, reviews: List[Dict]) -> TrustSignal:
        bodies = [r.get("body", "") for r in reviews]
        # Hash exact duplicates
        hashes = [hashlib.md5(b.strip().lower().encode()).hexdigest() for b in bodies]
        exact_dup_count = len(bodies) - len(set(hashes))

        # Near-duplicate via sampling (O(n²) is too slow for large sets)
        sample_size = min(200, len(bodies))
        sampled = bodies[:sample_size]
        near_dup_pairs = 0
        for i in range(len(sampled)):
            for j in range(i + 1, min(i + 20, len(sampled))):
                ratio = SequenceMatcher(None, sampled[i], sampled[j]).ratio()
                if ratio >= self.DUPLICATE_SIMILARITY:
                    near_dup_pairs += 1

        near_dup_pct = near_dup_pairs / max(1, sample_size) * 100
        total_dup_pct = (exact_dup_count / len(reviews) * 100) + near_dup_pct * 0.5

        penalty = min(20, int(total_dup_pct * 2))
        severity = "high" if total_dup_pct > 10 else "medium" if total_dup_pct > 5 else "low"

        return TrustSignal(
            signal_name="duplicate_reviews",
            value=round(total_dup_pct, 1),
            penalty=penalty,
            description=f"{round(total_dup_pct, 1)}% duplicate or near-duplicate review content detected.",
            severity=severity,
        )

    # ─── Signal 2: Rating vs sentiment mismatch ───────────────────────────────

    def _check_mismatch(
        self,
        reviews: List[Dict],
        sentiment_labels: Dict[str, str],
    ) -> TrustSignal:
        mismatches = 0
        eligible = 0

        for r in reviews:
            label = sentiment_labels.get(r["review_id"], "neutral")
            rating = float(r.get("rating", 3))
            eligible += 1

            # High star + negative text OR low star + positive text
            if (rating >= 4 and label == "negative") or (rating <= 2 and label == "positive"):
                mismatches += 1

        mismatch_pct = (mismatches / eligible * 100) if eligible else 0
        penalty = min(15, int(mismatch_pct * 0.6))
        severity = "high" if mismatch_pct > 20 else "medium" if mismatch_pct > 10 else "low"

        return TrustSignal(
            signal_name="rating_sentiment_mismatch",
            value=round(mismatch_pct, 1),
            penalty=penalty,
            description=f"{round(mismatch_pct, 1)}% of reviews have star rating contradicting their text sentiment.",
            severity=severity,
        )

    # ─── Signal 3: Burst / spike detection ────────────────────────────────────

    def _check_burst(self, reviews: List[Dict]) -> TrustSignal:
        dated = []
        for r in reviews:
            d = r.get("date")
            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d)
                except Exception:
                    continue
            if isinstance(d, datetime):
                dated.append((d, r.get("rating", 3)))

        if len(dated) < 10:
            return TrustSignal("burst_pattern", 0.0, 0, "Insufficient date data.", "low")

        dated.sort(key=lambda x: x[0])
        total = len(dated)

        max_burst_pct = 0.0
        burst_dates = []
        for i, (d, _) in enumerate(dated):
            window_end = d + timedelta(days=self.BURST_WINDOW_DAYS)
            window_count = sum(1 for dd, _ in dated if d <= dd <= window_end)
            pct = window_count / total
            if pct > max_burst_pct:
                max_burst_pct = pct
                burst_dates = [d.strftime("%Y-%m-%d")]

        is_burst = max_burst_pct >= self.BURST_THRESHOLD
        penalty = min(20, int(max_burst_pct * 40)) if is_burst else 0
        severity = "high" if max_burst_pct > 0.35 else "medium" if is_burst else "low"

        desc = (
            f"Suspicious: {round(max_burst_pct*100, 1)}% of reviews posted "
            f"within a 7-day window around {burst_dates[0] if burst_dates else 'unknown'}."
            if is_burst
            else "No unusual review spike patterns detected."
        )

        return TrustSignal(
            signal_name="burst_pattern",
            value=round(max_burst_pct * 100, 1),
            penalty=penalty,
            description=desc,
            severity=severity,
        )

    # ─── Signal 4: Generic / low-information reviews ──────────────────────────

    def _check_generic(self, reviews: List[Dict]) -> TrustSignal:
        short_count = sum(
            1 for r in reviews
            if len(r.get("body", "").split()) <= self.GENERIC_MAX_LENGTH
        )
        ratio = short_count / len(reviews)
        penalty = min(15, int(max(0, ratio - 0.20) * 60))
        severity = "high" if ratio > 0.40 else "medium" if ratio > 0.25 else "low"

        return TrustSignal(
            signal_name="generic_reviews",
            value=round(ratio * 100, 1),
            penalty=penalty,
            description=f"{round(ratio*100, 1)}% of reviews are very short (≤30 words) — potentially low-quality or incentivised.",
            severity=severity,
        )

    # ─── Signal 5: Verified purchase ratio ────────────────────────────────────

    def _check_verified(self, reviews: List[Dict]) -> TrustSignal:
        verified = sum(1 for r in reviews if r.get("verified_purchase", False))
        pct = verified / len(reviews) * 100
        # Penalty for LOW verified ratio
        penalty = min(15, int(max(0, 80 - pct) * 0.3))
        severity = "high" if pct < 50 else "medium" if pct < 70 else "low"

        return TrustSignal(
            signal_name="verified_purchase_ratio",
            value=round(pct, 1),
            penalty=penalty,
            description=f"{round(pct, 1)}% of reviews are from verified purchases.",
            severity=severity,
        )

    # ─── Adjusted rating ──────────────────────────────────────────────────────

    def _adjusted_rating(self, reviews: List[Dict], signals: List[TrustSignal]) -> float:
        ratings = [float(r.get("rating", 3)) for r in reviews]
        if not ratings:
            return 0.0
        raw_avg = np.mean(ratings)
        trust_penalty = sum(s.penalty for s in signals) / 100.0
        adjusted = raw_avg * (1 - trust_penalty * 0.3)
        return round(max(1.0, min(5.0, adjusted)), 2)

    # ─── Grade & summary ──────────────────────────────────────────────────────

    @staticmethod
    def _score_to_grade(score: int) -> str:
        if score >= 85: return "A"
        if score >= 70: return "B"
        if score >= 55: return "C"
        if score >= 40: return "D"
        return "F"

    def _build_summary(self, score: int, signals: List[TrustSignal]) -> str:
        high_signals = [s for s in signals if s.severity == "high"]
        if score >= 80:
            return "Reviews appear genuine and reliable."
        elif score >= 60:
            return f"Some trust concerns: {'; '.join(s.signal_name for s in high_signals[:2])}."
        else:
            return f"Low trust — significant manipulation signals: {'; '.join(s.signal_name for s in high_signals[:3])}."
