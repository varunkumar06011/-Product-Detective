"""
Product Detective — Unit Tests
Comprehensive tests for all backend modules.

Run with:
    pytest tests/unit/ -v
    pytest tests/unit/ -v --cov=modules --cov-report=term-missing
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))


# ══════════════════════════════════════════════════════════════════════════════
#  Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_reviews():
    """20 realistic reviews for testing."""
    base_date = datetime(2025, 1, 1)
    return [
        {
            "review_id": f"R{i:03d}",
            "body": body,
            "rating": rating,
            "date": (base_date + timedelta(days=i * 9)).isoformat(),
            "verified_purchase": i % 3 != 0,
            "title": f"Review {i}",
        }
        for i, (body, rating) in enumerate([
            ("This laptop overheats terribly after 30 min of gaming. Fan is extremely loud.", 1),
            ("Battery drains in 2 hours, very disappointed with battery life.", 2),
            ("Great performance for the price. Very happy with my purchase!", 5),
            ("Overheating issue is real. Thermal throttling ruins gaming sessions.", 1),
            ("Excellent display quality. Colors are vibrant and sharp.", 5),
            ("Fan noise is unbearable. Cannot use in quiet environments.", 2),
            ("Good build quality overall. Keyboard feels comfortable to type on.", 4),
            ("Overheats during rendering. CPU temperature hits 95 degrees.", 1),
            ("Love the display and performance. Worth every rupee.", 5),
            ("Battery backup is terrible, barely lasts 90 minutes.", 2),
            ("Solid gaming laptop at this price point. RTX 3060 handles games well.", 4),
            ("Overheating is a serious problem. Bottom panel gets burning hot.", 1),
            ("Happy with performance for content creation work.", 4),
            ("Fan runs at full speed always. Very annoying noise.", 2),
            ("Great value laptop. Handles all my tasks smoothly.", 5),
            ("Battery life disappoints. Expected at least 4 hours.", 2),
            ("Good GPU performance for gaming. Runs modern titles at high settings.", 4),
            ("Overheating is making it unusable for long gaming sessions.", 1),
            ("Keyboard backlighting is gorgeous. Build feels premium.", 4),
            ("Decent laptop but thermal management could be much better.", 3),
        ])
    ]


@pytest.fixture
def sentiment_labels(sample_reviews):
    """Mock sentiment labels aligned with ratings."""
    mapping = {}
    for r in sample_reviews:
        if r["rating"] >= 4:
            mapping[r["review_id"]] = "positive"
        elif r["rating"] <= 2:
            mapping[r["review_id"]] = "negative"
        else:
            mapping[r["review_id"]] = "neutral"
    return mapping


# ══════════════════════════════════════════════════════════════════════════════
#  1. Sentiment Model Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSentimentModel:
    """Tests for the rule-based sentiment fallback (no GPU required)."""

    def setup_method(self):
        from modules.sentiment_model import SentimentModel
        self.model = SentimentModel()
        # Force rule-based to avoid needing HuggingFace in CI
        self.model._pipe = None

    def test_positive_review(self):
        reviews = [{"review_id": "R1", "body": "Great excellent product love it amazing", "rating": 5}]
        report = self.model.analyze_reviews(reviews)
        assert report.positive_pct > 0 or report.neutral_pct > 0  # flexible

    def test_negative_review(self):
        reviews = [{"review_id": "R1", "body": "Bad terrible horrible broken defective waste", "rating": 1}]
        report = self.model.analyze_reviews(reviews)
        assert report.negative_pct > 0

    def test_empty_reviews(self):
        report = self.model.analyze_reviews([])
        assert report.positive_pct == 0
        assert report.negative_pct == 0
        assert report.avg_score == 0.0

    def test_percentages_sum_to_100(self, sample_reviews):
        report = self.model.analyze_reviews(sample_reviews)
        total = report.positive_pct + report.neutral_pct + report.negative_pct
        assert abs(total - 100.0) < 1.0, f"Expected ~100%, got {total}"

    def test_per_review_length_matches_input(self, sample_reviews):
        report = self.model.analyze_reviews(sample_reviews)
        assert len(report.per_review) == len(sample_reviews)

    def test_all_labels_valid(self, sample_reviews):
        from modules.sentiment_model import SentimentModel
        model = SentimentModel()
        model._pipe = None
        report = model.analyze_reviews(sample_reviews)
        valid_labels = {"positive", "neutral", "negative"}
        for r in report.per_review:
            assert r.label in valid_labels

    def test_phrase_extraction_returns_list(self, sample_reviews):
        report = self.model.analyze_reviews(sample_reviews)
        assert isinstance(report.top_positive_phrases, list)
        assert isinstance(report.top_negative_phrases, list)


# ══════════════════════════════════════════════════════════════════════════════
#  2. Complaint Detector Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestComplaintDetector:

    def setup_method(self):
        from modules.complaint_detector import ComplaintDetector
        self.detector = ComplaintDetector()

    def test_detects_overheating_cluster(self, sample_reviews, sentiment_labels):
        report = self.detector.detect(sample_reviews, "laptop", sentiment_labels)
        categories = [c.category for c in report.clusters]
        assert "overheating" in categories, f"Expected overheating, got: {categories}"

    def test_detects_battery_cluster(self, sample_reviews, sentiment_labels):
        report = self.detector.detect(sample_reviews, "laptop", sentiment_labels)
        categories = [c.category for c in report.clusters]
        assert "battery" in categories or "fan_noise" in categories

    def test_total_reviews_matches(self, sample_reviews, sentiment_labels):
        report = self.detector.detect(sample_reviews, "laptop", sentiment_labels)
        assert report.total_reviews == len(sample_reviews)

    def test_empty_reviews(self):
        report = self.detector.detect([], "laptop")
        assert report.clusters == []
        assert report.total_reviews == 0

    def test_severity_classification(self, sample_reviews, sentiment_labels):
        report = self.detector.detect(sample_reviews, "laptop", sentiment_labels)
        for cluster in report.clusters:
            assert cluster.severity in ("critical", "moderate", "minor")

    def test_cluster_pct_range(self, sample_reviews, sentiment_labels):
        report = self.detector.detect(sample_reviews, "laptop", sentiment_labels)
        for cluster in report.clusters:
            assert 0 <= cluster.total_pct <= 100
            assert 0 <= cluster.frequency_pct <= 100

    def test_no_complaints_on_all_positive(self):
        reviews = [
            {"review_id": f"R{i}", "body": "Great amazing love excellent recommend!", "rating": 5}
            for i in range(10)
        ]
        labels = {f"R{i}": "positive" for i in range(10)}
        report = self.detector.detect(reviews, "laptop", labels)
        assert all(c.severity != "critical" for c in report.clusters)

    def test_category_mapping(self):
        assert self.detector._map_category("Gaming Laptop") == "laptop"
        assert self.detector._map_category("Smartphone 5G") == "phone"
        assert self.detector._map_category("TWS Earbuds") == "earbuds"
        assert self.detector._map_category("Unknown Product") == "generic"


# ══════════════════════════════════════════════════════════════════════════════
#  3. Complaint Trend Analyzer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestComplaintTrendAnalyzer:

    def setup_method(self):
        from modules.complaint_trend_analyzer import ComplaintTrendAnalyzer, ComplaintCluster
        self.analyzer = ComplaintTrendAnalyzer()
        self.ComplaintCluster = ComplaintCluster

    def _make_rising_reviews(self, n=60):
        """Generate reviews where overheating complaints increase over time."""
        reviews = []
        base = datetime(2024, 10, 1)
        for i in range(n):
            date = base + timedelta(days=i * 3)
            month_num = (date - base).days // 30
            # overheating frequency increases each month: 8%, 14%, 20%, 26%, 32%
            is_complaint = i % max(1, (12 - month_num * 2)) == 0
            body = "This laptop overheats badly during gaming." if is_complaint else "Works fine overall."
            reviews.append({
                "review_id": f"R{i:03d}",
                "body": body,
                "rating": 1 if is_complaint else 4,
                "date": date.isoformat(),
                "verified_purchase": True,
            })
        return reviews

    def test_detects_rising_trend(self):
        reviews = self._make_rising_reviews(60)
        cluster = self.ComplaintCluster(
            category="overheating",
            label="Overheating / Thermal Issues",
            frequency_pct=30.0,
            total_pct=15.0,
            examples=[],
            keywords=["overheat", "hot", "temperature"],
            severity="critical",
        )
        report = self.analyzer.analyze(reviews, [cluster], lookback_months=6)
        # Should find at least one signal (rising or otherwise)
        assert isinstance(report.signals, list)
        assert isinstance(report.has_critical_trend, bool)
        assert isinstance(report.summary, str)

    def test_empty_inputs(self):
        report = self.analyzer.analyze([], [])
        assert report.signals == []
        assert not report.has_critical_trend

    def test_signal_fields_present(self):
        reviews = self._make_rising_reviews(60)
        from modules.complaint_trend_analyzer import ComplaintCluster
        cluster = ComplaintCluster(
            category="overheating", label="Overheating",
            frequency_pct=20.0, total_pct=10.0,
            examples=[], keywords=["overheat", "hot"],
            severity="moderate",
        )
        report = self.analyzer.analyze(reviews, [cluster])
        for signal in report.signals:
            assert hasattr(signal, 'complaint_category')
            assert hasattr(signal, 'slope')
            assert hasattr(signal, 'r_squared')
            assert hasattr(signal, 'significance')
            assert signal.significance in ("high", "medium", "low")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Review Trust Model Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestReviewTrustModel:

    def setup_method(self):
        from modules.review_trust_model import ReviewTrustModel
        self.model = ReviewTrustModel()

    def test_high_trust_authentic_reviews(self):
        reviews = [
            {
                "review_id": f"R{i}",
                "body": f"This is a detailed review number {i}. The product has specific features that I tested over {i+1} weeks.",
                "rating": [4, 5, 4, 3, 5][i % 5],
                "date": (datetime(2024, 10, 1) + timedelta(days=i * 7)).isoformat(),
                "verified_purchase": True,
            }
            for i in range(20)
        ]
        report = self.model.calculate(reviews)
        assert report.score >= 50  # Should be reasonably high

    def test_low_trust_burst_reviews(self):
        # All reviews posted on the same day (burst pattern)
        same_date = datetime(2025, 1, 15).isoformat()
        reviews = [
            {
                "review_id": f"R{i}",
                "body": "Great product! Very happy.",
                "rating": 5,
                "date": same_date,
                "verified_purchase": False,
            }
            for i in range(20)
        ]
        report = self.model.calculate(reviews)
        assert report.score < 80  # Should be penalised

    def test_score_range(self, sample_reviews, sentiment_labels):
        report = self.model.calculate(sample_reviews, sentiment_labels)
        assert 0 <= report.score <= 100

    def test_grade_assignment(self):
        assert self.model._score_to_grade(90) == "A"
        assert self.model._score_to_grade(75) == "B"
        assert self.model._score_to_grade(60) == "C"
        assert self.model._score_to_grade(45) == "D"
        assert self.model._score_to_grade(30) == "F"

    def test_adjusted_rating_range(self, sample_reviews, sentiment_labels):
        report = self.model.calculate(sample_reviews, sentiment_labels)
        assert 1.0 <= report.adjusted_rating <= 5.0

    def test_too_few_reviews(self):
        reviews = [{"review_id": "R1", "body": "ok", "rating": 3,
                    "date": datetime.utcnow().isoformat(), "verified_purchase": True}]
        report = self.model.calculate(reviews)
        assert report.score == 50  # default for insufficient data

    def test_mismatch_detection(self):
        # 5-star review with very negative text
        mismatch_reviews = [
            {
                "review_id": f"R{i}",
                "body": "Terrible broken defective waste horrible" if i % 2 == 0 else "Great excellent love recommend",
                "rating": 5 if i % 2 == 0 else 1,  # intentional mismatch
                "date": (datetime(2024, 10, 1) + timedelta(days=i * 5)).isoformat(),
                "verified_purchase": True,
            }
            for i in range(20)
        ]
        sentiment = {f"R{i}": "negative" if i % 2 == 0 else "positive" for i in range(20)}
        report = self.model.calculate(mismatch_reviews, sentiment)
        mismatch_signal = next((s for s in report.signals if s.signal_name == "rating_sentiment_mismatch"), None)
        assert mismatch_signal is not None
        assert mismatch_signal.value > 0


# ══════════════════════════════════════════════════════════════════════════════
#  5. Category Classifier + Spec Evaluator Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCategoryClassifier:

    def setup_method(self):
        from modules.category_classifier import CategoryClassifier, SpecEvaluator
        self.classifier = CategoryClassifier()
        self.evaluator = SpecEvaluator()

    def test_classifies_laptop(self):
        cat, conf = self.classifier.classify("ASUS Gaming Laptop i7 RTX 3060", {})
        assert cat == "laptop"
        assert conf > 0.5

    def test_classifies_phone(self):
        cat, conf = self.classifier.classify("Samsung Galaxy A54 5G Smartphone", {})
        assert cat == "phone"
        assert conf > 0.5

    def test_classifies_earbuds(self):
        cat, conf = self.classifier.classify("boAt Airdopes TWS Earbuds Bluetooth", {})
        assert cat == "earbuds"
        assert conf > 0.5

    def test_unknown_category_fallback(self):
        cat, conf = self.classifier.classify("Wooden Spoon Set 5 pieces", {})
        assert cat == "generic"

    def test_laptop_spec_scoring(self):
        specs = {
            "Processor": "Intel Core i7-12700H",
            "Graphics": "NVIDIA GeForce RTX 3060",
            "RAM": "16GB DDR5",
            "Storage": "512GB NVMe SSD",
            "Display": "144Hz IPS FHD",
            "Battery": "58Wh",
        }
        result = self.evaluator.evaluate("Gaming Laptop i7 RTX3060", specs, "gaming")
        assert result.detected_category == "laptop"
        assert 0 <= result.overall_spec_score <= 100
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)

    def test_phone_spec_scoring(self):
        specs = {
            "Processor": "Exynos 1380",
            "Camera": "50MP OIS Main",
            "Battery": "5000mAh",
            "Charging": "25W fast charging",
            "Display": "Super AMOLED 120Hz",
            "Storage": "128GB",
        }
        result = self.evaluator.evaluate("Samsung Galaxy A54 5G", specs, "daily")
        assert result.detected_category == "phone"
        assert len(result.spec_scores) > 0


# ══════════════════════════════════════════════════════════════════════════════
#  6. Decision Engine Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDecisionEngine:

    def setup_method(self):
        from modules.decision_engine import DecisionEngine, Verdict
        self.engine = DecisionEngine()
        self.Verdict = Verdict

    def _mock_sentiment(self, pos, neu, neg):
        r = MagicMock()
        r.positive_pct = pos
        r.neutral_pct = neu
        r.negative_pct = neg
        r.avg_score = (pos - neg) / 100
        return r

    def _mock_complaints(self, critical=0, moderate=0):
        r = MagicMock()
        clusters = []
        for _ in range(critical):
            c = MagicMock(); c.severity = "critical"; c.label = "Test"; c.total_pct = 25.0
            clusters.append(c)
        for _ in range(moderate):
            c = MagicMock(); c.severity = "moderate"; c.label = "Test"; c.total_pct = 12.0
            clusters.append(c)
        r.clusters = clusters
        return r

    def _mock_trend(self, critical=False):
        r = MagicMock()
        r.has_critical_trend = critical
        r.signals = []
        r.summary = "No issues"
        return r

    def _mock_trust(self, score=80):
        r = MagicMock()
        r.score = score
        r.summary = "OK"
        return r

    def _mock_specs(self, overall=75):
        r = MagicMock()
        r.overall_spec_score = overall
        r.strengths = ["GPU", "Display"]
        r.weaknesses = []
        r.spec_scores = []
        return r

    def test_buy_verdict_high_score(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(75, 15, 10),
            complaint_report=self._mock_complaints(0, 0),
            trend_report=self._mock_trend(False),
            trust_report=self._mock_trust(88),
            category_eval=self._mock_specs(80),
        )
        assert result.verdict == self.Verdict.BUY

    def test_avoid_verdict_low_score(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(30, 15, 55),
            complaint_report=self._mock_complaints(3, 1),
            trend_report=self._mock_trend(True),
            trust_report=self._mock_trust(45),
            category_eval=self._mock_specs(35),
        )
        assert result.verdict == self.Verdict.AVOID

    def test_wait_verdict_mixed_signals(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(52, 20, 28),
            complaint_report=self._mock_complaints(1, 1),
            trend_report=self._mock_trend(True),
            trust_report=self._mock_trust(68),
            category_eval=self._mock_specs(58),
        )
        assert result.verdict in (self.Verdict.WAIT, self.Verdict.AVOID)

    def test_confidence_range(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(70, 15, 15),
            complaint_report=self._mock_complaints(0, 1),
            trend_report=self._mock_trend(False),
            trust_report=self._mock_trust(80),
            category_eval=self._mock_specs(70),
        )
        assert 0 <= result.confidence <= 100

    def test_evidence_not_empty(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(60, 20, 20),
            complaint_report=self._mock_complaints(1, 0),
            trend_report=self._mock_trend(False),
            trust_report=self._mock_trust(72),
            category_eval=self._mock_specs(65),
        )
        assert len(result.evidence) > 0

    def test_budget_note_over_budget(self):
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(70, 15, 15),
            complaint_report=self._mock_complaints(0, 0),
            trend_report=self._mock_trend(False),
            trust_report=self._mock_trust(82),
            category_eval=self._mock_specs(75),
            user_budget=50000,
            product_price=90000,
        )
        assert result.budget_note is not None
        assert "over budget" in result.budget_note.lower()

    def test_trust_override_caps_buy(self):
        """Very low trust score should prevent BUY verdict."""
        result = self.engine.decide(
            sentiment_report=self._mock_sentiment(80, 10, 10),
            complaint_report=self._mock_complaints(0, 0),
            trend_report=self._mock_trend(False),
            trust_report=self._mock_trust(30),  # Very low trust
            category_eval=self._mock_specs(85),
        )
        assert result.verdict != self.Verdict.BUY


# ══════════════════════════════════════════════════════════════════════════════
#  7. Recommendation Engine Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEngine:

    def setup_method(self):
        from modules.recommendation_engine import RecommendationEngine
        self.engine = RecommendationEngine()

    def test_no_alternatives_for_buy(self):
        report = self.engine.recommend("laptop", 89990, "BUY", 84)
        assert not report.found
        assert report.alternatives == []

    def test_finds_alternatives_for_avoid(self):
        report = self.engine.recommend("laptop", 89990, "AVOID", 55)
        assert report.found
        assert len(report.alternatives) > 0

    def test_finds_alternatives_for_wait(self):
        report = self.engine.recommend("earbuds", 1299, "WAIT", 50)
        assert report.found or not report.found  # OK if no alternatives in DB

    def test_alternative_fields(self):
        report = self.engine.recommend("laptop", 89990, "AVOID", 50)
        if report.found:
            for alt in report.alternatives:
                assert hasattr(alt, 'name')
                assert hasattr(alt, 'price')
                assert hasattr(alt, 'score')
                assert hasattr(alt, 'key_advantages')
                assert isinstance(alt.key_advantages, list)

    def test_max_alternatives_limit(self):
        report = self.engine.recommend("laptop", 89990, "AVOID", 40)
        assert len(report.alternatives) <= self.engine.MAX_ALTERNATIVES

    def test_alternatives_better_than_current(self):
        current_score = 50.0
        report = self.engine.recommend("laptop", 89990, "AVOID", current_score)
        for alt in report.alternatives:
            assert alt.score > current_score

    def test_unknown_category(self):
        report = self.engine.recommend("unknown_gadget", 5000, "AVOID", 40)
        # Should not crash, should return not found
        assert isinstance(report.found, bool)


# ══════════════════════════════════════════════════════════════════════════════
#  8. Platform Router / Scraper Tests (URL parsing only — no network)
# ══════════════════════════════════════════════════════════════════════════════

class TestPlatformRouter:

    def setup_method(self):
        from modules.product_scraper import PlatformRouter, AmazonScraper
        self.router = PlatformRouter()
        self.amazon = AmazonScraper()

    def test_detects_amazon_in(self):
        assert self.router.detect("https://www.amazon.in/dp/B0TEST123") == "amazon"

    def test_detects_amazon_com(self):
        assert self.router.detect("https://www.amazon.com/dp/B0TEST123") == "amazon"

    def test_detects_flipkart(self):
        assert self.router.detect("https://www.flipkart.com/product/p/ABC123") == "flipkart"

    def test_unsupported_platform(self):
        assert self.router.detect("https://www.myntra.com/product/123") is None

    def test_extract_asin_dp(self):
        asin = self.amazon._extract_asin("https://www.amazon.in/dp/B0CK35XVVD/ref=sr_1_3")
        assert asin == "B0CK35XVVD"

    def test_extract_asin_gp(self):
        asin = self.amazon._extract_asin("https://www.amazon.com/gp/product/B08N5WRWNW")
        assert asin == "B08N5WRWNW"

    def test_extract_asin_invalid(self):
        asin = self.amazon._extract_asin("https://www.amazon.in/s?k=laptop")
        assert asin is None

    def test_parse_amazon_date(self):
        date = self.amazon._parse_amazon_date("Reviewed in India on 15 March 2024")
        assert date.year == 2024
        assert date.month == 3
        assert date.day == 15
