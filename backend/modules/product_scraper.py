"""
Product Detective — Product Scraper Module
Extracts product data from Amazon, Flipkart, and other e-commerce platforms.
Uses BeautifulSoup for static pages, Selenium for dynamic JS-rendered content.
"""

import asyncio
import re
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ProductReview:
    review_id: str
    rating: float
    title: str
    body: str
    date: datetime
    verified_purchase: bool
    helpful_votes: int = 0
    reviewer_name: str = ""


@dataclass
class ProductData:
    url: str
    source: str                  # "amazon" | "flipkart"
    product_id: str
    title: str
    price: float
    currency: str
    rating: float
    total_ratings: int
    review_count: int
    description: str
    specifications: Dict[str, str]
    category_raw: str
    reviews: List[ProductReview] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class PlatformRouter:
    """Detects platform from URL and routes to the correct scraper."""

    PLATFORMS = {
        "amazon.in": "amazon",
        "amzn.in": "amazon",
        "amazon.com": "amazon",
        "amazon.co.uk": "amazon",
        "amazon.de": "amazon",
        "amazon.ca": "amazon",
        "amazon.com.au": "amazon",
        "amazon.sg": "amazon",
        "amazon.ae": "amazon",
        "amazon.sa": "amazon",
        "flipkart.com": "flipkart",
    }

    # Domains that are Amazon infrastructure (images, CDN, short links)
    # but NOT product pages — we reject these with a helpful message
    AMAZON_NON_PRODUCT_DOMAINS = {
        "m.media-amazon.com",
        "images-na.ssl-images-amazon.com",
        "ecx.images-amazon.com",
        "ssl-images-amazon.com",
    }

    IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg")

    @classmethod
    def detect(cls, url: str) -> Optional[str]:
        parsed = urlparse(url)
        hostname = parsed.netloc.lstrip("www.")
        path = parsed.path.lower()

        # Reject image URLs with a helpful error
        if any(path.endswith(ext) for ext in cls.IMAGE_EXTENSIONS):
            raise ValueError(
                "This looks like an image URL, not a product page. "
                "Please paste the full product page URL from your browser's address bar "
                "(e.g. https://www.amazon.in/dp/B0XXXXXXXX)."
            )

        # Reject Amazon CDN/image domains
        if hostname in cls.AMAZON_NON_PRODUCT_DOMAINS:
            raise ValueError(
                "This is an Amazon image/CDN URL, not a product page. "
                "Please paste the full product page URL from your browser's address bar."
            )

        # Exact match first
        platform = cls.PLATFORMS.get(hostname)
        if platform:
            return platform

        # Fuzzy match: any domain containing "amazon" → amazon
        if "amazon" in hostname:
            return "amazon"
        if "flipkart" in hostname:
            return "flipkart"

        return None


class SeleniumDriver:
    """Context-managed Selenium Chrome driver (headless)."""

    def __enter__(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(f"user-agent={settings.SCRAPER_USER_AGENT}")
        options.add_argument("--window-size=1920,1080")
        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return self.driver

    def __exit__(self, *args):
        try:
            self.driver.quit()
        except Exception:
            pass


class AmazonScraper:
    """
    Scrapes Amazon product pages including title, price, specs, and paginated reviews.
    Handles anti-bot measures via randomised delays and headless Selenium.
    """

    REVIEW_PAGES_MAX = 2  # 2 pages × 10 reviews = max 20 reviews (Fastest for Free Tier)

    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                "User-Agent": settings.SCRAPER_USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Referer": "https://www.google.com/",
            },
            timeout=15.0, # Shorter timeout to fail fast to Selenium if needed
            follow_redirects=True,
        )

    async def scrape(self, url: str) -> ProductData:
        logger.info(f"Targeting Amazon URL: {url}")
        
        product_id = ""
        try:
            # 1. Fetch the product page first (follows redirects)
            html = await self._fetch_page(url)

            # 2. Extract ASIN from final state (HTML or final URL might be better but we only have HTML here)
            product_id = self._extract_asin(url) or self._extract_asin_from_html(html)
            
            if not product_id:
                return ProductData(url=url, source="amazon", product_id="", title="",
                                   price=0, currency="INR", rating=0, total_ratings=0,
                                   review_count=0, description="", specifications={},
                                   category_raw="", error="Could not extract ASIN from page")

            logger.info(f"Resolved ASIN: {product_id}")
            product = self._parse_product_page(html, url, product_id)

            # 3. Fetch more reviews from reviews page if needed
            if len(product.reviews) < 5:
                more_reviews = await self._fetch_all_reviews(product_id)
                
                # Deduplicate by ID
                existing_ids = {r.review_id for r in product.reviews}
                for r in more_reviews:
                    if r.review_id not in existing_ids:
                        product.reviews.append(r)
            
            product.review_count = len(product.reviews)
            return product
        except Exception as e:
            logger.error(f"Amazon scrape failed for {url}: {e}")
            return ProductData(url=url, source="amazon", product_id=product_id,
                               title="", price=0, currency="INR", rating=0,
                               total_ratings=0, review_count=0, description="",
                               specifications={}, category_raw="", error=str(e))

    def _extract_asin(self, url: str) -> Optional[str]:
        patterns = [
            r"/dp/([A-Z0-9]{10})",
            r"/gp/product/([A-Z0-9]{10})",
            r"/product/([A-Z0-9]{10})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_asin_from_html(self, html: str) -> Optional[str]:
        """Try several common places for ASIN in Amazon HTML."""
        soup = BeautifulSoup(html, "lxml")
        
        # 1. Canonical link: "https://www.amazon.in/Realme-Narzo-60X-5G-Green/dp/B0CKN1C8T3"
        canonical = soup.select_one("link[rel='canonical']")
        if canonical and canonical.get("href"):
            asin = self._extract_asin(canonical.get("href"))
            if asin: return asin
            
        # 2. Input#asin 
        asin_input = soup.select_one("input#asin")
        if asin_input and asin_input.get("value"):
            return asin_input.get("value")
            
        # 3. From text "ASIN: B0..."
        match = re.search(r"asin\":\s*\"([A-Z0-9]{10})\"", html, re.IGNORECASE)
        if match:
            return match.group(1)
            
        return None

    async def _fetch_page(self, url: str) -> str:
        """Fetch HTML with httpx; fall back to Selenium if blocked."""
        resp = await self.session.get(url)
        if resp.status_code == 200 and "captcha" not in resp.text.lower():
            return resp.text

        # Fallback: Selenium
        logger.warning(f"httpx blocked ({resp.status_code}), switching to Selenium")
        return self._selenium_fetch(url)

    def _selenium_fetch(self, url: str) -> str:
        with SeleniumDriver() as driver:
            driver.set_page_load_timeout(30)
            try:
                driver.get(url)
                # Wait for title OR captcha
                WebDriverWait(driver, 10).until(
                    lambda d: d.find_elements(By.ID, "productTitle") or d.find_elements(By.ID, "captchacharacters")
                )
                return driver.page_source
            except Exception as e:
                logger.error(f"Selenium fetch failed: {e}")
                return ""

    def _parse_product_page(self, html: str, url: str, product_id: str) -> ProductData:
        soup = BeautifulSoup(html, "lxml")

        title = self._text(soup, "#productTitle") or "Unknown Product"
        price_str = self._text(soup, ".a-price-whole") or "0"
        price = float(re.sub(r"[^\d.]", "", price_str) or 0)

        rating_str = self._text(soup, "span.a-icon-alt") or "0"
        rating = float(rating_str.split()[0]) if rating_str else 0

        ratings_str = self._text(soup, "#acrCustomerReviewText") or "0"
        total_ratings = int(re.sub(r"[^\d]", "", ratings_str) or 0)

        description = self._text(soup, "#productDescription") or ""

        # Specs table
        specs = {}
        for row in soup.select("#productDetails_techSpec_section_1 tr, "
                                "#technicalSpecifications_section_1 tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                specs[th.get_text(strip=True)] = td.get_text(strip=True)

        # Category breadcrumb
        crumbs = soup.select("#wayfinding-breadcrumbs_feature_div a")
        category_raw = " > ".join(c.get_text(strip=True) for c in crumbs)

        images = [
            img.get("src", "") for img in soup.select("#altImages img")
            if img.get("src", "").startswith("https://")
        ]

        return ProductData(
            url=url, source="amazon", product_id=product_id,
            title=title, price=price, currency="INR",
            rating=rating, total_ratings=total_ratings, review_count=0,
            description=description, specifications=specs,
            category_raw=category_raw, images=images[:8],
            reviews=self._parse_reviews_page(html)  # Try to find reviews on main page too
        )

    async def _fetch_all_reviews(self, asin: str) -> List[ProductReview]:
        """Paginate through Amazon review pages."""
        reviews = []
        base_url = f"https://www.amazon.in/product-reviews/{asin}"
        params = {
            "pageNumber": 1,
            "sortBy": "recent",
            "reviewerType": "all_reviews",
        }

        for page in range(1, self.REVIEW_PAGES_MAX + 1):
            params["pageNumber"] = page
            url_with_params = f"{base_url}?pageNumber={page}&sortBy=recent&reviewerType=all_reviews"
            try:
                resp = await self.session.get(base_url, params=params)
                
                html = ""
                if resp.status_code == 200 and "captcha" not in resp.text.lower():
                    html = resp.text
                else:
                    logger.warning(f"Review page {page} blocked, attempting batch Selenium fetch")
                    # If blocked, we fetch the remaining pages in one Selenium session
                    remaining_htmls = self._selenium_fetch_reviews_batch(base_url, page, self.REVIEW_PAGES_MAX)
                    for r_html in remaining_htmls:
                        page_reviews = self._parse_reviews_page(r_html)
                        if page_reviews:
                            reviews.extend(page_reviews)
                    break # Batch fetch handles the rest

                if not html:
                    break

                page_reviews = self._parse_reviews_page(html)
                if not page_reviews:
                    break

                reviews.extend(page_reviews)
                await asyncio.sleep(0.8)  # polite delay

                if len(reviews) >= settings.MAX_REVIEWS_PER_PRODUCT:
                    break

            except Exception as e:
                logger.warning(f"Review page {page} failed: {e}")
                break

        return reviews[:settings.MAX_REVIEWS_PER_PRODUCT]

    def _selenium_fetch_reviews_batch(self, base_url: str, start_page: int, end_page: int) -> List[str]:
        """Fetch multiple review pages using a single Selenium session to save RAM."""
        htmls = []
        with SeleniumDriver() as driver:
            for page in range(start_page, end_page + 1):
                url = f"{base_url}?pageNumber={page}&sortBy=recent&reviewerType=all_reviews"
                try:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-hook='review']"))
                    )
                    htmls.append(driver.page_source)
                    time.sleep(1) # Small gap between pages
                except Exception as e:
                    logger.warning(f"Selenium batch fetch failed at page {page}: {e}")
                    break
        return htmls

    def _parse_reviews_page(self, html: str) -> List[ProductReview]:
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        for block in soup.select("[data-hook='review']"):
            try:
                review_id = block.get("id", "")
                rating_el = block.select_one("[data-hook='review-star-rating'] span")
                rating = float(
                    (rating_el.get_text(strip=True) or "0").split()[0]
                ) if rating_el else 0

                title = self._text(block, "[data-hook='review-title'] span:last-child")
                body = self._text(block, "[data-hook='review-body'] span")
                date_str = self._text(block, "[data-hook='review-date']") or ""

                # Parse "Reviewed in India on 12 March 2024"
                date = self._parse_amazon_date(date_str)
                verified = bool(block.select_one("[data-hook='avp-badge']"))

                helpful_str = self._text(block, "[data-hook='helpful-vote-statement']") or "0"
                helpful = int(re.search(r"\d+", helpful_str).group()) if re.search(r"\d+", helpful_str) else 0

                reviewer = self._text(block, ".a-profile-name") or "Anonymous"

                reviews.append(ProductReview(
                    review_id=review_id, rating=rating, title=title or "",
                    body=body or "", date=date, verified_purchase=verified,
                    helpful_votes=helpful, reviewer_name=reviewer,
                ))
            except Exception:
                continue

        return reviews

    def _parse_amazon_date(self, date_str: str) -> datetime:
        """Parse 'Reviewed in India on 12 March 2024'."""
        try:
            match = re.search(r"(\d+\s+\w+\s+\d{4})", date_str)
            if match:
                return datetime.strptime(match.group(1), "%d %B %Y")
        except Exception:
            pass
        return datetime.utcnow()

    def _text(self, soup, selector: str) -> Optional[str]:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None


class FlipkartScraper:
    """Scrapes Flipkart product pages."""

    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={"User-Agent": settings.SCRAPER_USER_AGENT},
            timeout=settings.SCRAPER_TIMEOUT,
        )

    async def scrape(self, url: str) -> ProductData:
        logger.info(f"Scraping Flipkart: {url}")
        try:
            resp = await self.session.get(url)
            soup = BeautifulSoup(resp.text, "lxml")
            return self._parse(soup, url)
        except Exception as e:
            logger.error(f"Flipkart scrape error: {e}")
            return ProductData(url=url, source="flipkart", product_id="",
                               title="", price=0, currency="INR", rating=0,
                               total_ratings=0, review_count=0, description="",
                               specifications={}, category_raw="", error=str(e))

    def _parse(self, soup: BeautifulSoup, url: str) -> ProductData:
        title = self._text(soup, "span.B_NuCI") or "Unknown"
        price_str = self._text(soup, "div._30jeq3._16Jk6d") or "0"
        price = float(re.sub(r"[^\d]", "", price_str) or 0)

        rating_str = self._text(soup, "div._3LWZlK") or "0"
        rating = float(rating_str) if rating_str else 0

        specs = {}
        for row in soup.select("table._14cfVK tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                specs[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)

        product_id = re.search(r"/p/([A-Z0-9]+)", url)
        pid = product_id.group(1) if product_id else ""

        return ProductData(
            url=url, source="flipkart", product_id=pid,
            title=title, price=price, currency="INR",
            rating=rating, total_ratings=0, review_count=0,
            description="", specifications=specs, category_raw="",
        )

    def _text(self, soup, selector: str) -> Optional[str]:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None


class ProductScraper:
    """
    Public interface for the scraper module.
    Auto-detects platform and delegates to the appropriate scraper.
    """

    def __init__(self):
        self.scrapers = {
            "amazon": AmazonScraper(),
            "flipkart": FlipkartScraper(),
        }

    async def scrape(self, url: str) -> ProductData:
        platform = PlatformRouter.detect(url)
        if not platform:
            raise ValueError(f"Unsupported platform for URL: {url}")

        scraper = self.scrapers.get(platform)
        if not scraper:
            raise ValueError(f"No scraper for platform: {platform}")

        return await scraper.scrape(url)
