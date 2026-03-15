"""
Product Detective — Integration Tests
End-to-end tests for the FastAPI endpoints.
Uses TestClient (no real server needed).

Run with:
    pytest tests/integration/ -v
"""

import pytest
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from fastapi.testclient import TestClient


# ── Mock the database and cache so tests don't need MongoDB/Redis ──────────────

@pytest.fixture(autouse=True)
def mock_db_and_cache():
    with patch("utils.database.connect_db", new_callable=AsyncMock), \
         patch("utils.database.disconnect_db", new_callable=AsyncMock), \
         patch("utils.cache.init_cache", new_callable=AsyncMock), \
         patch("utils.cache.get_cache", new_callable=AsyncMock, return_value=None), \
         patch("utils.cache.set_cache", new_callable=AsyncMock, return_value=True):
        yield


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


# ── Mock scraper result ────────────────────────────────────────────────────────

def make_mock_product(n_reviews=30):
    from modules.product_scraper import ProductData, ProductReview

    reviews = []
    for i in range(n_reviews):
        date = datetime(2024, 10 + (i % 3), 1 + (i % 28))
        body = (
            "This laptop overheats badly during gaming sessions."
            if i % 4 == 0
            else "Battery life is terrible, barely lasts 2 hours."
            if i % 5 == 0
            else "Great performance and good display quality overall."
        )
        reviews.append(ProductReview(
            review_id=f"R{i:03d}",
            rating=float(1 if i % 4 == 0 else 5),
            title="Review",
            body=body,
            date=date,
            verified_purchase=i % 3 != 0,
        ))

    return ProductData(
        url="https://www.amazon.in/dp/B0TEST1234",
        source="amazon",
        product_id="B0TEST1234",
        title="Test Gaming Laptop Pro 15",
        price=89990.0,
        currency="INR",
        rating=3.8,
        total_ratings=1247,
        review_count=n_reviews,
        description="A powerful gaming laptop.",
        specifications={
            "Processor": "Intel Core i7-12700H",
            "Graphics": "NVIDIA GeForce RTX 3060",
            "RAM": "16GB DDR5",
            "Storage": "512GB NVMe SSD",
            "Display": "144Hz IPS FHD",
            "Battery": "58Wh",
        },
        category_raw="Electronics > Computers > Laptops > Gaming Laptops",
        reviews=reviews,
        error=None,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Health endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        with patch("api.routes.health.get_db") as mock_db:
            mock_db.return_value.command = AsyncMock()
            response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_has_required_fields(self, client):
        with patch("api.routes.health.get_db") as mock_db:
            mock_db.return_value.command = AsyncMock()
            response = client.get("/api/v1/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "service" in data


# ══════════════════════════════════════════════════════════════════════════════
#  Investigation endpoint — full pipeline integration
# ══════════════════════════════════════════════════════════════════════════════

class TestInvestigationEndpoint:

    @pytest.fixture
    def mock_scraper(self):
        product = make_mock_product(30)
        with patch("api.routes.verdict.scraper") as mock:
            mock.scrape = AsyncMock(return_value=product)
            yield mock

    def test_investigation_returns_200(self, client, mock_scraper):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "https://www.amazon.in/dp/B0TEST1234",
            "budget": 90000,
            "purpose": "gaming",
            "priority": "performance",
        })
        assert response.status_code == 200

    def test_investigation_response_fields(self, client, mock_scraper):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "https://www.amazon.in/dp/B0TEST1234",
            "budget": 90000,
            "purpose": "gaming",
            "priority": "performance",
        })
        if response.status_code == 200:
            data = response.json()
            required_fields = [
                "case_id", "verdict", "confidence", "product_title",
                "clue_cards", "evidence", "alternatives",
            ]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"

    def test_verdict_is_valid_value(self, client, mock_scraper):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "https://www.amazon.in/dp/B0TEST1234",
            "budget": 90000,
            "purpose": "gaming",
            "priority": "performance",
        })
        if response.status_code == 200:
            data = response.json()
            assert data["verdict"] in ("BUY", "WAIT", "AVOID")

    def test_confidence_range(self, client, mock_scraper):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "https://www.amazon.in/dp/B0TEST1234",
        })
        if response.status_code == 200:
            data = response.json()
            assert 0 <= data["confidence"] <= 100

    def test_clue_cards_present(self, client, mock_scraper):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "https://www.amazon.in/dp/B0TEST1234",
            "purpose": "gaming",
            "priority": "performance",
        })
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["clue_cards"], list)
            assert len(data["clue_cards"]) >= 1

    def test_invalid_url_returns_422(self, client):
        response = client.post("/api/v1/verdict/investigate", json={
            "url": "not-a-valid-url",
        })
        assert response.status_code == 422

    def test_missing_url_returns_422(self, client):
        response = client.post("/api/v1/verdict/investigate", json={
            "budget": 50000,
        })
        assert response.status_code == 422

    def test_scrape_error_returns_422(self, client):
        from modules.product_scraper import ProductData
        error_product = ProductData(
            url="https://www.amazon.in/dp/BADERROR",
            source="amazon", product_id="BADERROR",
            title="", price=0, currency="INR", rating=0,
            total_ratings=0, review_count=0, description="",
            specifications={}, category_raw="",
            error="Could not scrape this page",
        )
        with patch("api.routes.verdict.scraper") as mock:
            mock.scrape = AsyncMock(return_value=error_product)
            response = client.post("/api/v1/verdict/investigate", json={
                "url": "https://www.amazon.in/dp/BADERROR",
            })
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  Analysis endpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalysisEndpoints:

    def test_sentiment_endpoint(self, client):
        response = client.post("/api/v1/analysis/sentiment", json={
            "reviews": [
                {"review_id": "R1", "body": "Great excellent product!", "rating": 5},
                {"review_id": "R2", "body": "Terrible broken waste!", "rating": 1},
                {"review_id": "R3", "body": "Average nothing special.", "rating": 3},
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "positive_pct" in data
        assert "negative_pct" in data
        total = data["positive_pct"] + data["neutral_pct"] + data["negative_pct"]
        assert abs(total - 100.0) < 1.0

    def test_complaints_endpoint(self, client):
        response = client.post("/api/v1/analysis/complaints", json={
            "reviews": [
                {"review_id": f"R{i}", "body": "Laptop overheats badly after 30 minutes of gaming.", "rating": 1}
                for i in range(10)
            ] + [
                {"review_id": f"P{i}", "body": "Great performance and value for money.", "rating": 5}
                for i in range(10)
            ],
            "product_category": "Gaming Laptop",
            "sentiment_labels": {f"R{i}": "negative" for i in range(10)} |
                                 {f"P{i}": "positive" for i in range(10)},
        })
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert "total_reviews" in data

    def test_trust_endpoint(self, client):
        response = client.post("/api/v1/analysis/trust", json={
            "reviews": [
                {
                    "review_id": f"R{i}",
                    "body": f"This is my detailed review number {i}. Tested for {i+1} weeks.",
                    "rating": [4, 5, 3, 4, 5][i % 5],
                    "date": f"2024-{10 + i%3:02d}-{1 + i%27:02d}T00:00:00",
                    "verified_purchase": True,
                }
                for i in range(15)
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert 0 <= data["score"] <= 100

    def test_specs_endpoint(self, client):
        response = client.post("/api/v1/analysis/specs", json={
            "product_title": "ASUS ROG Strix Gaming Laptop",
            "specifications": {
                "Processor": "Intel Core i7-12700H",
                "Graphics": "NVIDIA RTX 3070",
                "RAM": "16GB DDR5",
                "Storage": "1TB NVMe SSD",
                "Display": "165Hz QHD IPS",
                "Battery": "90Wh",
            },
            "user_purpose": "gaming",
        })
        assert response.status_code == 200
        data = response.json()
        assert "detected_category" in data
        assert "overall_score" in data
        assert data["detected_category"] == "laptop"


# ══════════════════════════════════════════════════════════════════════════════
#  Recommendations endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendationsEndpoint:

    def test_get_alternatives_avoid(self, client):
        response = client.post("/api/v1/recommend/alternatives", json={
            "category": "laptop",
            "product_price": 89990,
            "verdict": "AVOID",
            "current_score": 50.0,
            "user_budget": 90000,
        })
        assert response.status_code == 200
        data = response.json()
        assert "found" in data
        assert "alternatives" in data

    def test_no_alternatives_for_buy(self, client):
        response = client.post("/api/v1/recommend/alternatives", json={
            "category": "laptop",
            "product_price": 89990,
            "verdict": "BUY",
            "current_score": 85.0,
        })
        assert response.status_code == 200
        data = response.json()
        assert not data["found"]
        assert data["alternatives"] == []
