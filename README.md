# 🔍 Product Detective
**AI-Powered Purchase Decision Intelligence**

> Investigate before you buy. The truth is in the reviews.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                             │
│  React + Tailwind + Framer Motion  ←→  FastAPI Backend         │
└──────────────────────────────┬──────────────────────────────────┘
                               │ REST API
┌──────────────────────────────▼──────────────────────────────────┐
│                    FASTAPI BACKEND (Python 3.11)                 │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │   Scraper   │  │  NLP Engine  │  │   Decision Engine     │  │
│  │  Amazon +   │  │  RoBERTa     │  │   Weighted Composite  │  │
│  │  Flipkart   │  │  Sentiment   │  │   BUY/WAIT/AVOID      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────────┬───────────┘  │
│         │                │                       │              │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌───────────▼───────────┐  │
│  │  Complaint  │  │   Trend      │  │  Recommendation       │  │
│  │  Detector   │  │  Analyzer    │  │  Engine               │  │
│  │  (TF-IDF +  │  │  (LinReg     │  │  (Category-aware      │  │
│  │  KMeans)    │  │  time series)│  │  product ranking)     │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  Trust      │  │  Category    │  │  MongoDB + Redis      │  │
│  │  Scorer     │  │  Classifier  │  │  Cache Layer          │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## ML Pipeline

```
Review Text
    │
    ▼
┌───────────────────────────────────┐
│  Stage 1: Sentiment Analysis      │
│  Model: RoBERTa (HuggingFace)     │
│  Output: pos/neu/neg per review   │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  Stage 2: Complaint Detection     │
│  Model: TF-IDF + Keyword Matching │
│  Output: complaint clusters       │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  Stage 3: Trend Analysis          │
│  Model: Linear Regression         │
│  Output: rising/falling signals   │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  Stage 4: Trust Scoring           │
│  Model: Rule-based anomaly det.   │
│  Output: 0-100 trust score        │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  Stage 5: Spec Evaluation         │
│  Model: Category-specific scoring │
│  Output: per-attribute scores     │
└────────────────┬──────────────────┘
                 │
                 ▼
┌───────────────────────────────────┐
│  Stage 6: Decision Engine         │
│  Model: Weighted composite        │
│  Output: BUY / WAIT / AVOID       │
└───────────────────────────────────┘
```

## Folder Structure

```
product_detective/
├── backend/
│   ├── main.py                          # FastAPI entry point
│   ├── api/
│   │   └── routes/
│   │       ├── verdict.py               # Core investigation endpoint
│   │       ├── scraper.py               # Direct scrape endpoint
│   │       ├── analysis.py              # Analysis-only endpoints
│   │       ├── recommendations.py       # Alternatives endpoint
│   │       └── health.py               # Health check
│   ├── modules/
│   │   ├── product_scraper.py           # Amazon + Flipkart scraper
│   │   ├── sentiment_model.py           # RoBERTa sentiment analysis
│   │   ├── complaint_detector.py        # TF-IDF + KMeans complaint clustering
│   │   ├── complaint_trend_analyzer.py  # Time series trend detection
│   │   ├── review_trust_model.py        # Fake review detection
│   │   ├── category_classifier.py       # Product category + spec scoring
│   │   ├── decision_engine.py           # BUY/WAIT/AVOID verdict engine
│   │   └── recommendation_engine.py     # Better alternative finder
│   └── utils/
│       ├── database.py                  # MongoDB connection
│       └── cache.py                     # Redis cache helpers
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── InvestigationBoard/      # Main detective board UI
│       │   ├── ClueCard/               # Individual clue card component
│       │   ├── VerdictStamp/           # BUY/WAIT/AVOID reveal
│       │   └── Alternatives/           # Better products panel
│       ├── pages/
│       │   ├── Home.jsx                # URL input + demo
│       │   ├── Interrogation.jsx       # User questions
│       │   └── Board.jsx               # Investigation board
│       ├── hooks/
│       │   ├── useInvestigation.js     # API call + state management
│       │   └── useClueReveal.js        # Card animation logic
│       └── store/
│           └── investigationStore.js    # Zustand state
├── ml/
│   ├── training/
│   │   └── train_pipeline.py           # Model training script
│   ├── saved_models/                   # Trained model artifacts
│   └── data/                           # Training datasets
├── config/
│   └── settings.py                     # Environment configuration
├── tests/
│   ├── unit/                           # Unit tests per module
│   └── integration/                    # End-to-end API tests
└── docker-compose.yml
```

## Quick Start

```bash
# 1. Clone and set up
git clone <repo>
cd product_detective

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload

# 3. Frontend
cd ../frontend
npm install
npm run dev

# 4. Or use Docker (everything at once)
docker-compose up --build
```

## API Endpoints

| Method | Endpoint                      | Description                        |
|--------|-------------------------------|------------------------------------|
| POST   | `/api/v1/verdict/investigate` | Full investigation pipeline        |
| GET    | `/api/v1/scrape/product`      | Scrape product data only           |
| POST   | `/api/v1/analysis/sentiment`  | Run sentiment on provided reviews  |
| GET    | `/api/v1/recommend/{id}`      | Get alternatives for a case        |
| GET    | `/api/v1/health`              | Health check                       |
| GET    | `/api/docs`                   | Swagger UI                         |

## Example Request

```bash
curl -X POST http://localhost:8000/api/v1/verdict/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.amazon.in/dp/B0XXXXXXXX",
    "budget": 90000,
    "purpose": "gaming",
    "priority": "performance"
  }'
```

## Decision Logic

```
composite_score = (
    sentiment_score  × 0.20  +
    complaint_score  × 0.25  +
    trend_score      × 0.20  +
    trust_score      × 0.15  +
    spec_score       × 0.15  +
    budget_score     × 0.05
)

composite >= 0.68  →  BUY
composite 0.44–0.68  →  WAIT
composite < 0.44   →  AVOID
```

## Training ML Models

```bash
# Train everything (uses synthetic data if no CSV provided)
python ml/training/train_pipeline.py --mode all

# With real data
python ml/training/train_pipeline.py \
  --mode all \
  --complaint-data ./ml/data/complaint_labels.csv \
  --verdict-data ./ml/data/verdict_labels.csv
```

## Environment Variables

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=product_detective
REDIS_URL=redis://localhost:6379
SENTIMENT_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest
ML_MODEL_PATH=./ml/saved_models
MAX_REVIEWS_PER_PRODUCT=500
SCRAPER_TIMEOUT=30
```

## Roadmap / Future Features

- [ ] Browser extension for in-page investigation
- [ ] Price history tracking + price drop alerts
- [ ] User feedback learning loop (RLHF-style)
- [ ] Real-time review monitoring (webhooks)
- [ ] Multi-language review support
- [ ] Price prediction model
- [ ] Seller reputation scoring
- [ ] Comparison mode (product A vs B)
