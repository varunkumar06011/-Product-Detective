"""
Product Detective — Complaint Trend Analyzer
Detects whether specific complaint types are increasing over time.
Uses time-series decomposition and linear regression on monthly complaint rates.
Flags complaints with statistically significant upward trends.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class MonthlyComplaintPoint:
    month: str          # "2025-01"
    complaint_pct: float
    count: int
    total_reviews: int


@dataclass
class TrendSignal:
    complaint_category: str
    label: str
    is_rising: bool
    slope: float                        # percentage points per month
    r_squared: float
    start_pct: float                    # 3 months ago
    end_pct: float                      # latest month
    change_pct: float                   # absolute change
    monthly_data: List[MonthlyComplaintPoint]
    significance: str                   # "high" | "medium" | "low"
    warning_message: Optional[str] = None


@dataclass
class TrendReport:
    signals: List[TrendSignal]
    has_critical_trend: bool
    summary: str


class ComplaintTrendAnalyzer:
    """
    For each complaint category, bins reviews by month and
    computes linear regression on the complaint frequency time series.

    A trend is flagged as significant if:
    - Slope > 2 pp/month AND R² > 0.6
    - Or the complaint rate has increased by > 10 pp in 3 months
    """

    MIN_MONTHS = 3
    SLOPE_THRESHOLD = 2.0    # percentage points per month
    R2_THRESHOLD = 0.55
    ABSOLUTE_CHANGE_THRESHOLD = 10.0  # pp

    def analyze(
        self,
        reviews: List[Dict[str, Any]],  # {"review_id", "body", "date", "rating"}
        complaint_clusters: List[Any],   # ComplaintCluster objects
        lookback_months: int = 6,
    ) -> TrendReport:

        if not reviews or not complaint_clusters:
            return TrendReport([], False, "Insufficient data for trend analysis.")

        # Bin all reviews by month
        monthly_totals = self._monthly_review_counts(reviews, lookback_months)
        signals = []

        for cluster in complaint_clusters:
            # Filter reviews that match this complaint category
            cluster_reviews = self._filter_cluster_reviews(reviews, cluster)
            if len(cluster_reviews) < 5:
                continue

            monthly_complaints = self._monthly_complaint_counts(
                cluster_reviews, monthly_totals, lookback_months
            )

            if len(monthly_complaints) < self.MIN_MONTHS:
                continue

            trend = self._compute_trend(monthly_complaints, cluster)
            if trend:
                signals.append(trend)

        # Sort by severity
        signals.sort(key=lambda s: (s.is_rising, abs(s.change_pct)), reverse=True)
        has_critical = any(s.significance == "high" and s.is_rising for s in signals)

        summary = self._build_summary(signals)
        return TrendReport(signals=signals, has_critical_trend=has_critical, summary=summary)

    # ─── Monthly binning ──────────────────────────────────────────────────────

    def _monthly_review_counts(
        self,
        reviews: List[Dict],
        lookback_months: int,
    ) -> Dict[str, int]:
        cutoff = datetime.utcnow() - timedelta(days=lookback_months * 30)
        counts: Dict[str, int] = defaultdict(int)
        for r in reviews:
            d = r.get("date")
            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d)
                except Exception:
                    continue
            if isinstance(d, datetime) and d >= cutoff:
                key = d.strftime("%Y-%m")
                counts[key] += 1
        return dict(counts)

    def _monthly_complaint_counts(
        self,
        cluster_reviews: List[Dict],
        monthly_totals: Dict[str, int],
        lookback_months: int,
    ) -> List[MonthlyComplaintPoint]:
        cutoff = datetime.utcnow() - timedelta(days=lookback_months * 30)
        complaint_counts: Dict[str, int] = defaultdict(int)

        for r in cluster_reviews:
            d = r.get("date")
            if isinstance(d, str):
                try:
                    d = datetime.fromisoformat(d)
                except Exception:
                    continue
            if isinstance(d, datetime) and d >= cutoff:
                key = d.strftime("%Y-%m")
                complaint_counts[key] += 1

        points = []
        for month in sorted(monthly_totals.keys()):
            total = monthly_totals.get(month, 0)
            count = complaint_counts.get(month, 0)
            if total > 0:
                pct = round(count / total * 100, 1)
                points.append(MonthlyComplaintPoint(
                    month=month, complaint_pct=pct,
                    count=count, total_reviews=total,
                ))
        return points

    # ─── Trend computation ────────────────────────────────────────────────────

    def _compute_trend(
        self,
        monthly_data: List[MonthlyComplaintPoint],
        cluster: Any,
    ) -> Optional[TrendSignal]:

        y = np.array([p.complaint_pct for p in monthly_data])
        x = np.arange(len(y), dtype=float)

        if len(y) < 2:
            return None

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2

        start_pct = float(y[0])
        end_pct = float(y[-1])
        change_pct = round(end_pct - start_pct, 1)

        is_rising = slope > 0
        abs_change = abs(change_pct)

        # Determine significance
        significant = (
            (abs(slope) >= self.SLOPE_THRESHOLD and r_squared >= self.R2_THRESHOLD)
            or abs_change >= self.ABSOLUTE_CHANGE_THRESHOLD
        )

        if not significant and abs_change < 5.0:
            return None  # Skip low-signal trends

        if abs(slope) >= self.SLOPE_THRESHOLD * 2 or abs_change >= 20:
            significance = "high"
        elif abs(slope) >= self.SLOPE_THRESHOLD or abs_change >= self.ABSOLUTE_CHANGE_THRESHOLD:
            significance = "medium"
        else:
            significance = "low"

        warning = None
        if is_rising and significance in ("high", "medium"):
            warning = (
                f"⚠ {cluster.label} complaints rose from {start_pct:.1f}% "
                f"→ {end_pct:.1f}% over {len(monthly_data)} months "
                f"(+{change_pct:.1f} pp). This may indicate a systemic defect."
            )

        return TrendSignal(
            complaint_category=cluster.category,
            label=cluster.label,
            is_rising=is_rising,
            slope=round(float(slope), 2),
            r_squared=round(float(r_squared), 3),
            start_pct=round(start_pct, 1),
            end_pct=round(end_pct, 1),
            change_pct=change_pct,
            monthly_data=monthly_data,
            significance=significance,
            warning_message=warning,
        )

    def _filter_cluster_reviews(
        self,
        reviews: List[Dict],
        cluster: Any,
    ) -> List[Dict]:
        keywords = cluster.keywords
        return [
            r for r in reviews
            if any(kw in r.get("body", "").lower() for kw in keywords)
        ]

    def _build_summary(self, signals: List[TrendSignal]) -> str:
        if not signals:
            return "No significant complaint trends detected."
        rising = [s for s in signals if s.is_rising and s.significance in ("high", "medium")]
        if not rising:
            return "Complaint patterns appear stable — no rising trends detected."
        topics = ", ".join(s.label for s in rising[:3])
        return f"Rising complaint trends detected in: {topics}. Investigate before purchasing."
