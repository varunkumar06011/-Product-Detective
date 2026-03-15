"""
Product Detective — Configuration
Environment-based settings using Pydantic BaseSettings
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Product Detective"
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = True
    USE_TRANSFORMERS: bool = False  # Set to True only if RAM > 2GB

    # Database
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "product_detective"

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL: int = 3600  # seconds

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://product-detective.vercel.app"

    @property
    def cors_origins(self) -> List[str]:
        return [s.strip() for s in self.ALLOWED_ORIGINS.split(",")]

    # Scraper
    SCRAPER_TIMEOUT: int = 30
    MAX_REVIEWS_PER_PRODUCT: int = 500
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ML Models
    ML_MODEL_PATH: str = "./ml/saved_models"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    BATCH_SIZE: int = 32

    # Investigation Config
    MIN_REVIEWS_REQUIRED: int = 20
    COMPLAINT_THRESHOLD: float = 0.15      # 15%+ = notable complaint
    TRUST_SPIKE_WINDOW_DAYS: int = 7
    TRUST_SPIKE_THRESHOLD: float = 0.25    # 25%+ in one week = suspicious
    TREND_MONTHS_LOOKBACK: int = 6

    # Category Confidence Thresholds
    BUY_THRESHOLD: float = 0.70
    WAIT_THRESHOLD: float = 0.45

    # Recommendation Engine
    MAX_ALTERNATIVES: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
