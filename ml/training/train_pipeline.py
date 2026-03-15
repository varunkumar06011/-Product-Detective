"""
Product Detective — ML Training Pipeline
Trains and evaluates:
  1. Complaint classifier (Random Forest on TF-IDF)
  2. Verdict predictor (Logistic Regression on aggregate features)

Usage:
  python ml/training/train_pipeline.py --mode all
  python ml/training/train_pipeline.py --mode complaint_classifier
  python ml/training/train_pipeline.py --mode verdict_predictor
"""

import argparse
import json
import logging
import os
import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    StratifiedKFold, cross_val_score, train_test_split
)
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score, roc_auc_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.calibration import CalibratedClassifierCV
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_pipeline")

MODEL_DIR = Path("./ml/saved_models")
DATA_DIR  = Path("./ml/data")
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
#  1. COMPLAINT CLASSIFIER
#     Input:  review text
#     Output: complaint category (overheating / battery / performance / other)
# ─────────────────────────────────────────────────────────────────────────────

def train_complaint_classifier(data_path: str = None) -> Dict:
    """
    Trains a TF-IDF + Random Forest complaint category classifier.
    If no data_path provided, uses synthetic bootstrap data for demonstration.
    """
    logger.info("Training complaint classifier...")

    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
    else:
        logger.warning("No training data found — generating synthetic samples.")
        df = _generate_synthetic_complaint_data()

    X = df["text"].fillna("").tolist()
    y = df["complaint_category"].tolist()

    classes = sorted(set(y))
    logger.info(f"Classes: {classes}")
    logger.info(f"Samples: {len(X)}")

    # Pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            stop_words="english",
            sublinear_tf=True,
            min_df=2,
        )),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_split=5,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    # Cross-validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X, y, cv=skf, scoring="f1_weighted", n_jobs=-1)
    logger.info(f"CV F1 (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # Final fit
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    report = classification_report(y_test, y_pred, output_dict=True)
    logger.info(f"\n{classification_report(y_test, y_pred)}")

    # Feature importance (top per class)
    tfidf: TfidfVectorizer = pipeline.named_steps["tfidf"]
    rf: RandomForestClassifier = pipeline.named_steps["clf"]
    feature_names = tfidf.get_feature_names_out()
    importances = rf.feature_importances_
    top_features = [
        feature_names[i]
        for i in np.argsort(importances)[::-1][:20]
    ]
    logger.info(f"Top features: {top_features[:10]}")

    # Save
    model_path = MODEL_DIR / "complaint_classifier.pkl"
    joblib.dump(pipeline, model_path)
    logger.info(f"Saved complaint classifier → {model_path}")

    return {
        "model": "complaint_classifier",
        "cv_f1": round(cv_scores.mean(), 4),
        "test_f1": round(f1_score(y_test, y_pred, average="weighted"), 4),
        "classes": classes,
        "top_features": top_features,
        "report": report,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  2. VERDICT PREDICTOR
#     Input:  aggregate features (sentiment%, complaints, trust, specs, price)
#     Output: BUY / WAIT / AVOID
# ─────────────────────────────────────────────────────────────────────────────

def train_verdict_predictor(data_path: str = None) -> Dict:
    """
    Trains a Logistic Regression verdict predictor on aggregate product features.
    Also trains a Gradient Boosting model and picks the better one.
    """
    logger.info("Training verdict predictor...")

    if data_path and Path(data_path).exists():
        df = pd.read_csv(data_path)
    else:
        logger.warning("No training data — generating synthetic aggregate features.")
        df = _generate_synthetic_verdict_data()

    FEATURE_COLS = [
        "positive_pct", "negative_pct", "avg_sentiment_score",
        "critical_complaint_count", "rising_trend_count",
        "trust_score", "spec_score",
        "price_budget_ratio", "verified_purchase_pct",
    ]

    X = df[FEATURE_COLS].values
    y = df["verdict"].tolist()

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Model A: Logistic Regression
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", CalibratedClassifierCV(
            LogisticRegression(
                C=1.0,
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            ),
            cv=5,
        )),
    ])

    # Model B: Gradient Boosting
    gb_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )),
    ])

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    lr_cv = cross_val_score(lr_pipeline, X, y_enc, cv=skf, scoring="f1_weighted")
    gb_cv = cross_val_score(gb_pipeline, X, y_enc, cv=skf, scoring="f1_weighted")

    logger.info(f"LR CV F1:  {lr_cv.mean():.4f} ± {lr_cv.std():.4f}")
    logger.info(f"GB CV F1:  {gb_cv.mean():.4f} ± {gb_cv.std():.4f}")

    best_pipeline = lr_pipeline if lr_cv.mean() >= gb_cv.mean() else gb_pipeline
    best_name = "logistic_regression" if lr_cv.mean() >= gb_cv.mean() else "gradient_boosting"
    logger.info(f"Selected: {best_name}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )
    best_pipeline.fit(X_train, y_train)
    y_pred = best_pipeline.predict(X_test)

    report = classification_report(y_test, y_pred, target_names=le.classes_, output_dict=True)
    logger.info(f"\n{classification_report(y_test, y_pred, target_names=le.classes_)}")

    # Feature importance heuristic (coefficient magnitude for LR)
    feature_importance = dict(zip(FEATURE_COLS, [0.0] * len(FEATURE_COLS)))

    # Save
    model_path   = MODEL_DIR / "verdict_predictor.pkl"
    encoder_path = MODEL_DIR / "verdict_label_encoder.pkl"
    joblib.dump(best_pipeline, model_path)
    joblib.dump(le, encoder_path)
    logger.info(f"Saved verdict predictor → {model_path}")

    return {
        "model": "verdict_predictor",
        "algorithm": best_name,
        "cv_f1": round(max(lr_cv.mean(), gb_cv.mean()), 4),
        "test_f1": round(f1_score(y_test, y_pred, average="weighted"), 4),
        "classes": list(le.classes_),
        "feature_cols": FEATURE_COLS,
        "report": report,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Synthetic data generators (bootstrapping before real data is collected)
# ─────────────────────────────────────────────────────────────────────────────

def _generate_synthetic_complaint_data() -> pd.DataFrame:
    """Generates labelled complaint text samples for bootstrapping."""
    samples = [
        # overheating
        ("This laptop gets extremely hot during gaming, thermal throttling noticed", "overheating"),
        ("The device overheats after 30 minutes of use, fan is constantly loud", "overheating"),
        ("Temperature spikes to 95°C under load, uncomfortable to use on lap", "overheating"),
        ("Burning smell from the bottom after extended use", "overheating"),
        # battery
        ("Battery drains in 2 hours, very disappointing backup time", "battery"),
        ("Can't last a full workday without charging, battery life is terrible", "battery"),
        ("Charging takes 3 hours but only gives 90 minutes of use", "battery"),
        # performance
        ("Lags when opening multiple tabs, slow performance", "performance"),
        ("Random crashes and freezes, unusable for work", "performance"),
        ("Stutters during video editing, CPU bottleneck", "performance"),
        # build_quality
        ("Plastic feels cheap, lid flexes too much when picked up", "build_quality"),
        ("Hinge broke after 6 months of normal use", "build_quality"),
        ("Screen wobbles, build quality not worth the price", "build_quality"),
        # positive (other category)
        ("Great laptop, very happy with performance and value", "other"),
        ("Excellent build quality, keyboard is comfortable", "other"),
        ("Battery lasts all day, very impressed", "other"),
    ] * 30  # replicate to increase dataset size

    df = pd.DataFrame(samples, columns=["text", "complaint_category"])
    # Add noise
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df


def _generate_synthetic_verdict_data() -> pd.DataFrame:
    """Generates labelled aggregate feature rows for verdict prediction."""
    rng = np.random.RandomState(42)
    n = 500
    rows = []

    for _ in range(n):
        # BUY: high positive, low complaints, high trust, good specs
        if rng.rand() < 0.33:
            row = {
                "positive_pct":          rng.uniform(60, 85),
                "negative_pct":          rng.uniform(5, 20),
                "avg_sentiment_score":   rng.uniform(0.4, 0.8),
                "critical_complaint_count": rng.randint(0, 2),
                "rising_trend_count":    rng.randint(0, 1),
                "trust_score":           rng.uniform(70, 95),
                "spec_score":            rng.uniform(65, 90),
                "price_budget_ratio":    rng.uniform(0.7, 1.0),
                "verified_purchase_pct": rng.uniform(75, 95),
                "verdict": "BUY",
            }
        # AVOID: high negative, many critical complaints, low trust
        elif rng.rand() < 0.5:
            row = {
                "positive_pct":          rng.uniform(20, 50),
                "negative_pct":          rng.uniform(35, 60),
                "avg_sentiment_score":   rng.uniform(-0.8, -0.2),
                "critical_complaint_count": rng.randint(2, 5),
                "rising_trend_count":    rng.randint(1, 4),
                "trust_score":           rng.uniform(30, 60),
                "spec_score":            rng.uniform(25, 55),
                "price_budget_ratio":    rng.uniform(0.9, 1.4),
                "verified_purchase_pct": rng.uniform(40, 70),
                "verdict": "AVOID",
            }
        # WAIT: mixed signals
        else:
            row = {
                "positive_pct":          rng.uniform(40, 65),
                "negative_pct":          rng.uniform(20, 40),
                "avg_sentiment_score":   rng.uniform(-0.2, 0.4),
                "critical_complaint_count": rng.randint(1, 3),
                "rising_trend_count":    rng.randint(0, 2),
                "trust_score":           rng.uniform(55, 75),
                "spec_score":            rng.uniform(45, 70),
                "price_budget_ratio":    rng.uniform(0.85, 1.2),
                "verified_purchase_pct": rng.uniform(60, 85),
                "verdict": "WAIT",
            }
        rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Product Detective ML Training Pipeline")
    parser.add_argument("--mode", choices=["all", "complaint_classifier", "verdict_predictor"],
                        default="all")
    parser.add_argument("--complaint-data", type=str, default=None)
    parser.add_argument("--verdict-data",   type=str, default=None)
    args = parser.parse_args()

    results = {}

    if args.mode in ("all", "complaint_classifier"):
        results["complaint"] = train_complaint_classifier(args.complaint_data)

    if args.mode in ("all", "verdict_predictor"):
        results["verdict"] = train_verdict_predictor(args.verdict_data)

    # Save training report
    report_path = MODEL_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"\n✅ Training complete. Report saved → {report_path}")
    for model, res in results.items():
        logger.info(f"  {model}: CV F1={res['cv_f1']}, Test F1={res['test_f1']}")
