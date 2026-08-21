"""
Product Detective — Review Processor
Central pre-processing pipeline that runs before all ML modules.
Cleans, deduplicates, normalises, and enriches raw review data.

This is the "ETL layer" sitting between the scraper output
and the analysis modules.
"""

import re
import logging
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProcessedReview:
    review_id: str
    body_raw: str
    body_clean: str         # normalised, lowercased, punctuation stripped
    body_tokens: List[str]  # word tokens for NLP
    rating: float
    date: Optional[datetime] = None
    verified_purchase: bool
    title: str
    content_hash: str       # MD5 for exact-duplicate detection
    word_count: int
    is_duplicate: bool = False
    language: str = "en"    # future: multi-language support


class ReviewProcessor:
    """
    Processes raw scraped reviews into a clean, analysis-ready format.

    Pipeline:
      1. Normalise text (HTML entities, whitespace, unicode)
      2. Exact-duplicate detection (hash-based)
      3. Near-duplicate flagging (first-pass by title)
      4. Language detection (stub — extend with langdetect)
      5. Token extraction
      6. Date normalisation
      7. Metadata enrichment (word count, verified flag)
    """

    MIN_BODY_LENGTH = 10      # characters — below this = almost certainly useless
    MAX_BODY_LENGTH = 2000    # characters — truncate for ML efficiency

    # Regex patterns for cleaning
    _HTML_TAG     = re.compile(r'<[^>]+>')
    _HTML_ENTITY  = re.compile(r'&[a-z]+;|&#\d+;')
    _URL          = re.compile(r'https?://\S+|www\.\S+')
    _WHITESPACE   = re.compile(r'\s+')
    _NON_ASCII    = re.compile(r'[^\x00-\x7F]+')   # keep for now, strip in token pass

    def process(self, raw_reviews: List[Dict[str, Any]]) -> List[ProcessedReview]:
        """
        Process a list of raw review dicts into ProcessedReview objects.
        Returns deduplicated, sorted-by-date list.
        """
        if not raw_reviews:
            return []

        processed = []
        seen_hashes = set()

        for r in raw_reviews:
            try:
                proc = self._process_one(r)

                # Exact duplicate check
                if proc.content_hash in seen_hashes:
                    proc.is_duplicate = True
                else:
                    seen_hashes.add(proc.content_hash)

                # Skip extremely short reviews
                if proc.word_count < 2:
                    continue

                processed.append(proc)

            except Exception as e:
                logger.warning(f"Failed to process review {r.get('review_id', '?')}: {e}")
                continue

        # Sort by date descending (most recent first); None dates go last
        processed.sort(key=lambda r: r.date or datetime.min, reverse=True)

        logger.info(
            f"Processed {len(processed)}/{len(raw_reviews)} reviews "
            f"({len(processed) - sum(1 for r in processed if r.is_duplicate)} unique)"
        )
        return processed

    def to_analysis_format(
        self, processed: List[ProcessedReview]
    ) -> List[Dict[str, Any]]:
        """
        Convert ProcessedReview list back to the dict format expected by
        sentiment_model, complaint_detector, etc.
        Excludes flagged duplicates.
        """
        return [
            {
                "review_id":        r.review_id,
                "body":             r.body_clean[:self.MAX_BODY_LENGTH],
                "rating":           r.rating,
                "date":             r.date.isoformat() if r.date else None,
                "verified_purchase": r.verified_purchase,
                "title":            r.title,
                "word_count":       r.word_count,
            }
            for r in processed
            if not r.is_duplicate
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _process_one(self, raw: Dict[str, Any]) -> ProcessedReview:
        body_raw = str(raw.get("body") or raw.get("text") or "")
        body_clean = self._clean_text(body_raw)
        tokens = self._tokenise(body_clean)

        return ProcessedReview(
            review_id=str(raw.get("review_id") or raw.get("id") or ""),
            body_raw=body_raw,
            body_clean=body_clean,
            body_tokens=tokens,
            rating=float(raw.get("rating") or 3),
            date=self._parse_date(raw.get("date")),
            verified_purchase=bool(raw.get("verified_purchase", False)),
            title=str(raw.get("title") or ""),
            content_hash=hashlib.md5(body_clean.lower().encode()).hexdigest(),
            word_count=len(tokens),
            language="en",
        )

    def _clean_text(self, text: str) -> str:
        text = self._HTML_TAG.sub(" ", text)
        text = self._HTML_ENTITY.sub(" ", text)
        text = self._URL.sub(" ", text)
        text = self._WHITESPACE.sub(" ", text)
        return text.strip()

    def _tokenise(self, text: str) -> List[str]:
        # Simple whitespace + punctuation tokeniser
        # Production: swap for spaCy or NLTK tokeniser
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        return [t for t in tokens if len(t) > 1]

    def _parse_date(self, date_val: Any) -> Optional[datetime]:
        """Parse a date value. Returns None if parsing fails (caller should filter None)."""
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d %B %Y", "%B %d, %Y"):
                try:
                    return datetime.strptime(date_val[:19], fmt[:len(date_val[:19])])
                except ValueError:
                    continue
        return None

    # ── Analytics helpers ──────────────────────────────────────────────────────

    def get_stats(self, processed: List[ProcessedReview]) -> Dict[str, Any]:
        """Return quick stats about the processed review set."""
        if not processed:
            return {}
        verified = sum(1 for r in processed if r.verified_purchase)
        duplicates = sum(1 for r in processed if r.is_duplicate)
        avg_words = sum(r.word_count for r in processed) / len(processed)
        dates = [r.date for r in processed]
        return {
            "total": len(processed),
            "unique": len(processed) - duplicates,
            "duplicates": duplicates,
            "verified": verified,
            "verified_pct": round(verified / len(processed) * 100, 1),
            "avg_word_count": round(avg_words, 1),
            "date_range": {
                "oldest": min(dates).isoformat(),
                "newest": max(dates).isoformat(),
            },
        }
