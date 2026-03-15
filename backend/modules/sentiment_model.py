"""
Product Detective — Sentiment Analysis Module
Classifies each review as positive / neutral / negative using a pre-trained
transformer (RoBERTa). Also extracts key topic phrases per sentiment bucket.
"""

import logging
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from collections import Counter

import numpy as np
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None

from sklearn.feature_extraction.text import TfidfVectorizer

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ReviewSentiment:
    review_id: str
    label: str          # "positive" | "neutral" | "negative"
    confidence: float   # 0.0 – 1.0
    score: float        # mapped to -1.0 – 1.0


@dataclass
class SentimentReport:
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    avg_score: float                       # -1 to 1
    top_positive_phrases: List[str]
    top_negative_phrases: List[str]
    per_review: List[ReviewSentiment]


class SentimentModel:
    """
    Transformer-based sentiment classifier.
    Falls back to a lightweight rule-based model when GPU is unavailable.
    """

    LABEL_MAP = {
        "LABEL_0": "negative",
        "LABEL_1": "neutral",
        "LABEL_2": "positive",
        # cardiffnlp/twitter-roberta-base-sentiment-latest labels
        "negative": "negative",
        "neutral": "neutral",
        "positive": "positive",
    }

    def __init__(self):
        self._pipe = None
        self._tfidf = TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=500,
            stop_words="english",
        )
        self._load_model()

    def _load_model(self):
        if not TRANSFORMERS_AVAILABLE:
            logger.info("Transformer support not installed. Using rule-based engine.")
            self._pipe = None
            return

        if not settings.USE_TRANSFORMERS:
            logger.info("USE_TRANSFORMERS is False. Using rule-based engine to save memory.")
            self._pipe = None
            return

        try:
            logger.info(f"Loading sentiment model: {settings.SENTIMENT_MODEL}")
            self._pipe = pipeline(
                "sentiment-analysis",
                model=settings.SENTIMENT_MODEL,
                tokenizer=settings.SENTIMENT_MODEL,
                top_k=1,
                device=-1,          # CPU; change to 0 for GPU
                truncation=True,
                max_length=512,
            )
            logger.info("✅ Transformer sentiment model loaded")
        except Exception as e:
            logger.warning(f"Transformer load failed: {e}. Using rule-based fallback.")
            self._pipe = None

    def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],  # [{"review_id": str, "body": str, "rating": float}]
    ) -> SentimentReport:

        if not reviews:
            return SentimentReport(0, 0, 0, 0.0, [], [], [])

        texts = [r["body"][:512] for r in reviews]
        labels = self._classify_batch(texts)

        per_review = []
        counts = Counter()
        scores = []

        for review, (label, confidence) in zip(reviews, labels):
            score = self._label_to_score(label)
            per_review.append(ReviewSentiment(
                review_id=review["review_id"],
                label=label,
                confidence=confidence,
                score=score,
            ))
            counts[label] += 1
            scores.append(score)

        total = len(reviews)
        pos_pct = float(round(counts["positive"] / total * 100, 1))
        neu_pct = float(round(counts["neutral"]  / total * 100, 1))
        neg_pct = float(round(counts["negative"] / total * 100, 1))
        avg_score = float(round(np.mean(scores), 3))

        # Extract top phrases per sentiment bucket
        pos_texts = [r["body"] for r, s in zip(reviews, per_review) if s.label == "positive"]
        neg_texts = [r["body"] for r, s in zip(reviews, per_review) if s.label == "negative"]

        pos_phrases = self._top_phrases(pos_texts, n=8)
        neg_phrases = self._top_phrases(neg_texts, n=8)

        return SentimentReport(
            positive_pct=pos_pct,
            neutral_pct=neu_pct,
            negative_pct=neg_pct,
            avg_score=avg_score,
            top_positive_phrases=pos_phrases,
            top_negative_phrases=neg_phrases,
            per_review=per_review,
        )

    def _classify_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        if self._pipe:
            return self._classify_transformer(texts)
        return self._classify_rule_based(texts)

    def _classify_transformer(self, texts: List[str]) -> List[Tuple[str, float]]:
        results = []
        batch_size = settings.BATCH_SIZE

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            outputs = self._pipe(batch)
            for output in outputs:
                item = output[0] if isinstance(output, list) else output
                label = self.LABEL_MAP.get(item["label"], "neutral")
                results.append((label, round(item["score"], 3)))

        return results

    def _classify_rule_based(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Simple lexicon-based fallback.
        Uses star rating if available (passed via a special prefix convention).
        """
        POSITIVE_WORDS = {
            "great", "excellent", "love", "amazing", "perfect", "good", "best",
            "fantastic", "awesome", "superb", "recommend", "happy", "satisfied",
            "worth", "quality", "durable", "fast", "smooth", "clear",
        }
        NEGATIVE_WORDS = {
            "bad", "worst", "terrible", "horrible", "broken", "defective",
            "disappoint", "waste", "poor", "cheap", "useless", "return",
            "refund", "overheat", "problem", "issue", "fail", "slow", "loud",
            "crack", "dead", "stop", "stop working",
        }
        results = []
        for text in texts:
            words = set(text.lower().split())
            pos_count = len(words & POSITIVE_WORDS)
            neg_count = len(words & NEGATIVE_WORDS)

            if pos_count > neg_count:
                results.append(("positive", min(0.5 + pos_count * 0.05, 0.95)))
            elif neg_count > pos_count:
                results.append(("negative", min(0.5 + neg_count * 0.05, 0.95)))
            else:
                results.append(("neutral", 0.5))
        return results

    def _top_phrases(self, texts: List[str], n: int = 8) -> List[str]:
        if len(texts) < 3:
            return []
        try:
            self._tfidf.fit(texts)
            feature_names = self._tfidf.get_feature_names_out()
            scores = self._tfidf.transform(texts).sum(axis=0).A1
            top_idx = scores.argsort()[::-1][:n]
            return [feature_names[i] for i in top_idx]
        except Exception:
            return []

    @staticmethod
    def _label_to_score(label: str) -> float:
        return {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(label, 0.0)
