"""
Product Detective — Complaint Detector Module
Clusters negative reviews into complaint categories using TF-IDF + KMeans.
Identifies major complaint types, frequency, and representative examples.
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


# ─── Domain-aware keyword seeds per product category ─────────────────────────
CATEGORY_COMPLAINT_SEEDS = {
    "laptop": {
        "overheating":     ["overheat", "hot", "temperature", "thermal", "burning", "throttle"],
        "battery":         ["battery", "drain", "charge", "backup", "hours"],
        "performance":     ["slow", "lag", "stutter", "crash", "freeze", "performance"],
        "build_quality":   ["build", "plastic", "flex", "flimsy", "creak", "lid"],
        "keyboard":        ["keyboard", "typing", "key", "backlit", "trackpad"],
        "display":         ["display", "screen", "flickering", "resolution", "brightness"],
        "fan_noise":       ["fan", "noise", "loud", "buzzing", "sound"],
    },
    "phone": {
        "battery":         ["battery", "drain", "charge", "backup"],
        "camera":          ["camera", "photo", "blur", "night", "quality"],
        "heating":         ["hot", "heat", "overheat", "warm"],
        "software":        ["update", "bug", "crash", "freeze", "ui", "software"],
        "build_quality":   ["scratch", "crack", "glass", "back", "plastic"],
        "connectivity":    ["wifi", "bluetooth", "network", "call", "signal"],
    },
    "earbuds": {
        "connectivity":    ["connect", "disconnect", "bluetooth", "drop", "pair"],
        "durability":      ["break", "stop", "dead", "work", "months"],
        "sound_quality":   ["bass", "sound", "audio", "quality", "mic", "clear"],
        "fit":             ["fit", "fall", "ear", "tip", "comfortable"],
        "charging_case":   ["case", "charge", "case open", "lid"],
    },
    "generic": {
        "quality":         ["quality", "cheap", "poor", "bad", "worse"],
        "durability":      ["break", "broke", "stop", "dead", "fail"],
        "value":           ["price", "expensive", "overpriced", "worth", "value"],
        "service":         ["service", "support", "return", "refund", "replace"],
    },
}


@dataclass
class ComplaintCluster:
    category: str           # e.g. "overheating"
    label: str              # human-readable: "Overheating / Thermal Issues"
    frequency_pct: float    # % of negative reviews in this cluster
    total_pct: float        # % of ALL reviews mentioning this complaint
    examples: List[str]     # 3 representative review snippets
    keywords: List[str]     # top keywords
    severity: str           # "critical" | "moderate" | "minor"


@dataclass
class ComplaintReport:
    clusters: List[ComplaintCluster]
    total_negative: int
    total_reviews: int
    category: str


class ComplaintDetector:
    """
    Two-stage complaint detection:
    1. Keyword seed matching for domain-specific complaints
    2. KMeans clustering on TF-IDF of remaining negative reviews
    """

    SEVERITY_THRESHOLDS = {"critical": 0.20, "moderate": 0.10}  # % of all reviews
    MIN_CLUSTER_SIZE = 3

    def detect(
        self,
        reviews: List[Dict[str, Any]],   # {"review_id", "body", "rating"}
        product_category: str = "generic",
        sentiment_labels: Dict[str, str] = None,  # review_id → label
    ) -> ComplaintReport:

        negative_reviews = [
            r for r in reviews
            if (sentiment_labels or {}).get(r["review_id"], "neutral") == "negative"
               or r.get("rating", 5) <= 2
        ]

        if not negative_reviews:
            return ComplaintReport([], 0, len(reviews), product_category)

        cat_key = self._map_category(product_category)
        seeds = CATEGORY_COMPLAINT_SEEDS.get(cat_key, CATEGORY_COMPLAINT_SEEDS["generic"])

        clusters = self._keyword_matching(negative_reviews, seeds, len(reviews))
        clusters = sorted(clusters, key=lambda c: c.total_pct, reverse=True)

        return ComplaintReport(
            clusters=clusters,
            total_negative=len(negative_reviews),
            total_reviews=len(reviews),
            category=product_category,
        )

    # ─── Keyword Matching ──────────────────────────────────────────────────────

    def _keyword_matching(
        self,
        negative_reviews: List[Dict],
        seeds: Dict[str, List[str]],
        total_reviews: int,
    ) -> List[ComplaintCluster]:

        buckets: Dict[str, List[Dict]] = defaultdict(list)

        for review in negative_reviews:
            body_lower = review["body"].lower()
            for category, keywords in seeds.items():
                if any(kw in body_lower for kw in keywords):
                    buckets[category].append(review)

        clusters = []
        for category, matched in buckets.items():
            if len(matched) < self.MIN_CLUSTER_SIZE:
                continue

            freq_pct = round(len(matched) / len(negative_reviews) * 100, 1)
            total_pct = round(len(matched) / total_reviews * 100, 1)

            severity = "minor"
            if total_pct >= self.SEVERITY_THRESHOLDS["critical"] * 100:
                severity = "critical"
            elif total_pct >= self.SEVERITY_THRESHOLDS["moderate"] * 100:
                severity = "moderate"

            examples = self._get_examples(matched, seeds[category])
            keywords = seeds[category][:5]

            clusters.append(ComplaintCluster(
                category=category,
                label=self._humanize(category),
                frequency_pct=freq_pct,
                total_pct=total_pct,
                examples=examples,
                keywords=keywords,
                severity=severity,
            ))

        return clusters

    # ─── KMeans clustering (used for overflow / unknown categories) ────────────

    def _kmeans_cluster(
        self,
        reviews: List[Dict],
        n_clusters: int = 5,
    ) -> List[Tuple[str, List[Dict]]]:
        texts = [r["body"] for r in reviews]

        vectorizer = TfidfVectorizer(
            max_features=200,
            stop_words="english",
            ngram_range=(1, 2),
        )
        try:
            X = vectorizer.fit_transform(texts)
        except Exception:
            return []

        n = min(n_clusters, len(reviews) - 1)
        if n < 2:
            return [("cluster_0", reviews)]

        # Find optimal k via silhouette
        best_k, best_score = 2, -1
        for k in range(2, min(n + 1, 8)):
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X)
            try:
                score = silhouette_score(X, labels, sample_size=min(500, len(reviews)))
                if score > best_score:
                    best_score, best_k = score, k
            except Exception:
                continue

        km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        cluster_labels = km.fit_predict(X)

        feature_names = vectorizer.get_feature_names_out()
        results = []
        for cluster_id in range(best_k):
            indices = [i for i, l in enumerate(cluster_labels) if l == cluster_id]
            cluster_reviews = [reviews[i] for i in indices]
            centroid = km.cluster_centers_[cluster_id]
            top_feature_idx = centroid.argsort()[::-1][:5]
            label = " / ".join(feature_names[i] for i in top_feature_idx[:3])
            results.append((label, cluster_reviews))

        return results

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _get_examples(self, reviews: List[Dict], keywords: List[str], n: int = 3) -> List[str]:
        scored = []
        for r in reviews:
            body = r["body"]
            kw_count = sum(1 for kw in keywords if kw in body.lower())
            scored.append((kw_count, body))
        scored.sort(reverse=True)
        snippets = []
        for _, body in scored[:n]:
            # Truncate to first sentence containing a keyword
            sentences = re.split(r"[.!?]", body)
            for sent in sentences:
                if any(kw in sent.lower() for kw in keywords):
                    snippets.append(sent.strip()[:200])
                    break
            else:
                snippets.append(body[:200])
        return snippets

    def _humanize(self, key: str) -> str:
        label_map = {
            "overheating": "Overheating / Thermal Issues",
            "battery": "Battery Life / Charging",
            "performance": "Performance / Speed Issues",
            "build_quality": "Build Quality / Durability",
            "keyboard": "Keyboard / Trackpad Issues",
            "display": "Display / Screen Problems",
            "fan_noise": "Fan Noise / Acoustics",
            "camera": "Camera / Photo Quality",
            "heating": "Device Heating",
            "software": "Software / UI Bugs",
            "connectivity": "Connectivity / Bluetooth Issues",
            "fit": "Fit / Comfort",
            "charging_case": "Charging Case Issues",
            "durability": "Durability / Longevity",
            "sound_quality": "Sound / Audio Quality",
            "quality": "Overall Quality",
            "value": "Price / Value",
            "service": "Customer Service",
        }
        return label_map.get(key, key.replace("_", " ").title())

    def _map_category(self, raw: str) -> str:
        raw_lower = raw.lower()
        if any(w in raw_lower for w in ["laptop", "notebook", "gaming pc"]):
            return "laptop"
        if any(w in raw_lower for w in ["phone", "smartphone", "mobile"]):
            return "phone"
        if any(w in raw_lower for w in ["earbud", "earphone", "headphone", "tws", "airpod"]):
            return "earbuds"
        return "generic"
