"""
Product Detective — Data Collection Script
Collects and labels product review data to build real training datasets.

Usage:
    # Collect reviews for a product and save to CSV
    python scripts/collect_data.py --url "https://www.amazon.in/dp/B0TEST123" --out data/raw/

    # Label complaint categories (interactive CLI)
    python scripts/collect_data.py --label data/raw/reviews.csv --out data/labelled/

    # Export merged labelled dataset for training
    python scripts/collect_data.py --merge data/labelled/ --out data/

The collected data feeds directly into:
    ml/training/train_pipeline.py --complaint-data data/complaint_labels.csv
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("collect_data")

# Complaint categories for labelling
COMPLAINT_CATEGORIES = [
    "overheating",
    "battery",
    "performance",
    "build_quality",
    "display",
    "keyboard",
    "fan_noise",
    "connectivity",
    "camera",
    "software",
    "durability",
    "fit",
    "sound_quality",
    "charging",
    "value",
    "other",
    "not_complaint",   # positive / neutral reviews
]

VERDICT_LABELS = ["BUY", "WAIT", "AVOID"]


# ── Collection ─────────────────────────────────────────────────────────────────

async def collect_reviews(url: str, out_dir: str):
    """Scrape a product and save reviews to CSV."""
    from modules.product_scraper import ProductScraper

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    scraper = ProductScraper()

    logger.info(f"Scraping: {url}")
    product = await scraper.scrape(url)

    if product.error:
        logger.error(f"Scrape failed: {product.error}")
        return

    logger.info(f"Got {len(product.reviews)} reviews for: {product.title}")

    # Save reviews CSV
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_id = product.product_id or "unknown"
    reviews_path = os.path.join(out_dir, f"reviews_{safe_id}_{ts}.csv")

    with open(reviews_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "review_id", "rating", "title", "body", "date",
            "verified_purchase", "helpful_votes",
        ])
        writer.writeheader()
        for r in product.reviews:
            writer.writerow({
                "review_id":        r.review_id,
                "rating":           r.rating,
                "title":            r.title,
                "body":             r.body.replace("\n", " "),
                "date":             r.date.isoformat(),
                "verified_purchase": r.verified_purchase,
                "helpful_votes":    r.helpful_votes,
            })

    # Save product metadata JSON
    meta_path = os.path.join(out_dir, f"product_{safe_id}_{ts}.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "product_id":    product.product_id,
            "source":        product.source,
            "title":         product.title,
            "price":         product.price,
            "rating":        product.rating,
            "total_ratings": product.total_ratings,
            "category_raw":  product.category_raw,
            "specifications": product.specifications,
            "url":           product.url,
            "scraped_at":    datetime.utcnow().isoformat(),
        }, f, indent=2)

    logger.info(f"Saved reviews → {reviews_path}")
    logger.info(f"Saved metadata → {meta_path}")


# ── Interactive Labelling CLI ──────────────────────────────────────────────────

def label_complaints(input_csv: str, out_dir: str):
    """
    Interactive CLI for labelling review complaint categories.
    Keyboard shortcuts: type the number next to a category and press Enter.
    Press 's' to skip, 'q' to quit and save progress.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    with open(input_csv, "r", encoding="utf-8") as f:
        reviews = list(csv.DictReader(f))

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"complaint_labels_{ts}.csv")

    labelled = []
    print(f"\n{'='*60}")
    print(" PRODUCT DETECTIVE — COMPLAINT LABELLING TOOL")
    print(f" {len(reviews)} reviews to label")
    print(f"{'='*60}\n")

    # Print category menu once
    print("CATEGORIES:")
    for i, cat in enumerate(COMPLAINT_CATEGORIES):
        print(f"  {i:2d}. {cat}")
    print("\n  s = skip   q = quit & save\n")

    for i, review in enumerate(reviews):
        rating = review.get("rating", "?")
        body   = review.get("body", "")[:300]

        print(f"\n[{i+1}/{len(reviews)}] ★{rating}")
        print(f"  {body}")
        print()

        while True:
            raw = input("  Category (0-15 | s | q): ").strip().lower()
            if raw == "q":
                _save_labels(labelled, out_path)
                print(f"\nSaved {len(labelled)} labels → {out_path}")
                return
            if raw == "s":
                break
            try:
                idx = int(raw)
                if 0 <= idx < len(COMPLAINT_CATEGORIES):
                    labelled.append({
                        "review_id":         review.get("review_id", ""),
                        "text":              review.get("body", ""),
                        "complaint_category": COMPLAINT_CATEGORIES[idx],
                        "rating":            rating,
                    })
                    break
                else:
                    print(f"  ⚠ Enter 0–{len(COMPLAINT_CATEGORIES)-1}")
            except ValueError:
                print("  ⚠ Invalid input")

    _save_labels(labelled, out_path)
    print(f"\n✅ Done! Saved {len(labelled)} labels → {out_path}")


def label_verdicts(input_json_dir: str, out_dir: str):
    """
    Interactive CLI for labelling aggregate product-level verdict (BUY/WAIT/AVOID).
    Each JSON file in input_json_dir should be a product metadata file.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    json_files = list(Path(input_json_dir).glob("product_*.json"))

    if not json_files:
        logger.error(f"No product JSON files found in {input_json_dir}")
        return

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"verdict_labels_{ts}.csv")
    labelled = []

    print(f"\n{'='*60}")
    print(" PRODUCT DETECTIVE — VERDICT LABELLING TOOL")
    print(f" {len(json_files)} products to label")
    print(f"{'='*60}\n")

    for i, jf in enumerate(json_files):
        with open(jf) as f:
            meta = json.load(f)

        print(f"\n[{i+1}/{len(json_files)}]")
        print(f"  Title:    {meta.get('title', '?')[:70]}")
        print(f"  Price:    ₹{meta.get('price', '?')}")
        print(f"  Rating:   ★{meta.get('rating', '?')}")
        print(f"  Category: {meta.get('category_raw', '?')[:50]}")
        print()

        while True:
            raw = input("  Verdict (0=BUY  1=WAIT  2=AVOID | s | q): ").strip().lower()
            if raw == "q":
                _save_verdict_labels(labelled, out_path)
                print(f"\nSaved {len(labelled)} verdicts → {out_path}")
                return
            if raw == "s":
                break
            try:
                idx = int(raw)
                if 0 <= idx < len(VERDICT_LABELS):
                    labelled.append({
                        "product_id":   meta.get("product_id", ""),
                        "title":        meta.get("title", ""),
                        "price":        meta.get("price", 0),
                        "rating":       meta.get("rating", 0),
                        "verdict":      VERDICT_LABELS[idx],
                    })
                    break
            except ValueError:
                pass
            print("  ⚠ Enter 0, 1, or 2")

    _save_verdict_labels(labelled, out_path)
    print(f"\n✅ Done! Saved {len(labelled)} verdicts → {out_path}")


# ── Merge labelled CSVs ────────────────────────────────────────────────────────

def merge_labels(labelled_dir: str, out_dir: str):
    """Merge all labelled CSVs in a directory into a single training file."""
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Complaints
    complaint_files = list(Path(labelled_dir).glob("complaint_labels_*.csv"))
    if complaint_files:
        merged = []
        for f in complaint_files:
            with open(f, encoding="utf-8") as fh:
                merged.extend(list(csv.DictReader(fh)))
        out = os.path.join(out_dir, "complaint_labels.csv")
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["review_id","text","complaint_category","rating"])
            writer.writeheader()
            writer.writerows(merged)
        logger.info(f"Merged {len(merged)} complaint labels → {out}")

    # Verdicts
    verdict_files = list(Path(labelled_dir).glob("verdict_labels_*.csv"))
    if verdict_files:
        merged = []
        for f in verdict_files:
            with open(f, encoding="utf-8") as fh:
                merged.extend(list(csv.DictReader(fh)))
        out = os.path.join(out_dir, "verdict_labels.csv")
        with open(out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["product_id","title","price","rating","verdict"])
            writer.writeheader()
            writer.writerows(merged)
        logger.info(f"Merged {len(merged)} verdict labels → {out}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _save_labels(rows: list, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        if not rows: return
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _save_verdict_labels(rows: list, path: str):
    _save_labels(rows, path)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Detective Data Collection")
    subparsers = parser.add_subparsers(dest="command")

    # collect
    p_collect = subparsers.add_parser("collect", help="Scrape a product URL")
    p_collect.add_argument("--url", required=True, help="Amazon/Flipkart product URL")
    p_collect.add_argument("--out", default="ml/data/raw", help="Output directory")

    # label-complaints
    p_label = subparsers.add_parser("label", help="Interactively label complaint categories")
    p_label.add_argument("--input", required=True, help="Input reviews CSV")
    p_label.add_argument("--out", default="ml/data/labelled", help="Output directory")

    # label-verdicts
    p_verdict = subparsers.add_parser("label-verdicts", help="Label product-level verdicts")
    p_verdict.add_argument("--input", required=True, help="Input directory with product JSON files")
    p_verdict.add_argument("--out", default="ml/data/labelled", help="Output directory")

    # merge
    p_merge = subparsers.add_parser("merge", help="Merge labelled CSVs for training")
    p_merge.add_argument("--input", required=True, help="Directory with labelled CSVs")
    p_merge.add_argument("--out", default="ml/data", help="Output directory")

    args = parser.parse_args()

    if args.command == "collect":
        asyncio.run(collect_reviews(args.url, args.out))
    elif args.command == "label":
        label_complaints(args.input, args.out)
    elif args.command == "label-verdicts":
        label_verdicts(args.input, args.out)
    elif args.command == "merge":
        merge_labels(args.input, args.out)
    else:
        parser.print_help()
