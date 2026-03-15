from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from modules.product_scraper import ProductScraper
from utils.database import save_product, get_product

logger = logging.getLogger(__name__)
router = APIRouter()
scraper = ProductScraper()


class ScrapeRequest(BaseModel):
    url: str
    force_refresh: bool = False


@router.post("/product")
async def scrape_product(req: ScrapeRequest):
    """
    Scrape a single product page.
    Returns title, price, specs, rating, and raw reviews.
    Cached in MongoDB — use force_refresh=true to bypass.
    """
    product = await scraper.scrape(req.url)
    if product.error:
        raise HTTPException(status_code=422, detail=product.error)

    # Persist to DB
    await save_product({
        "product_id": product.product_id,
        "source": product.source,
        "title": product.title,
        "price": product.price,
        "rating": product.rating,
        "review_count": product.review_count,
        "specifications": product.specifications,
        "category_raw": product.category_raw,
        "url": product.url,
    })

    return {
        "product_id": product.product_id,
        "source": product.source,
        "title": product.title,
        "price": product.price,
        "currency": product.currency,
        "rating": product.rating,
        "total_ratings": product.total_ratings,
        "review_count": product.review_count,
        "description": product.description[:500],
        "specifications": product.specifications,
        "category_raw": product.category_raw,
        "images": product.images,
        "reviews_preview": [
            {
                "rating": r.rating,
                "title": r.title,
                "body": r.body[:200],
                "date": r.date.isoformat(),
                "verified_purchase": r.verified_purchase,
            }
            for r in product.reviews[:5]
        ],
    }