# Product Detective — Complete Deployment Guide

## Prerequisites

| Tool        | Version  | Purpose                        |
|-------------|----------|--------------------------------|
| Python      | 3.11+    | Backend runtime                |
| Node.js     | 20+      | Frontend build                 |
| Docker      | 24+      | Containerised deployment       |
| MongoDB     | 7+       | Primary database               |
| Redis       | 7+       | Caching layer                  |

---

## Option A — Local Development (Fastest)

### 1. Clone and install
```bash
git clone https://github.com/yourname/product-detective.git
cd product-detective

# Install everything
make install
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your settings
```

### 3. Start services (MongoDB + Redis via Docker)
```bash
docker run -d -p 27017:27017 --name pd-mongo mongo:7
docker run -d -p 6379:6379  --name pd-redis redis:7-alpine
```

### 4. Train ML models (first time only)
```bash
make train
# Trains complaint classifier + verdict predictor using synthetic data.
# Output: ml/saved_models/complaint_classifier.pkl
#         ml/saved_models/verdict_predictor.pkl
```

### 5. Start backend
```bash
make dev-backend
# API running at http://localhost:8000
# Swagger UI at http://localhost:8000/api/docs
```

### 6. Start frontend (new terminal)
```bash
make dev-frontend
# App running at http://localhost:3000
```

---

## Option B — Docker Compose (Recommended for staging)

```bash
# Build and start everything
make docker-up

# Services:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/api/docs
#   MongoDB:   localhost:27017
#   Redis:     localhost:6379

# View logs
make docker-logs

# Stop everything
make docker-down
```

---

## Option C — Production VPS Deployment

### 1. Server setup (Ubuntu 22.04)
```bash
# Install Docker + Compose
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin

# Create app user
useradd -m -s /bin/bash detective
usermod -aG docker detective
```

### 2. Clone and configure
```bash
su - detective
git clone https://github.com/yourname/product-detective.git /opt/product-detective
cd /opt/product-detective

# Create production .env
cp backend/.env.example backend/.env
nano backend/.env
# Set: ENV=production, SECRET_KEY=<random-64-char>, DEBUG=false
```

### 3. SSL with Certbot + Nginx reverse proxy
```bash
apt install certbot python3-certbot-nginx nginx

# Create nginx config (replace yourdomain.com)
cat > /etc/nginx/sites-available/product-detective << 'EOF'
server {
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_read_timeout 120s;
    }
}
EOF

ln -s /etc/nginx/sites-available/product-detective /etc/nginx/sites-enabled/
certbot --nginx -d yourdomain.com
```

### 4. Deploy
```bash
cd /opt/product-detective
docker compose up -d
```

### 5. Auto-restart on reboot
```bash
cat > /etc/systemd/system/product-detective.service << 'EOF'
[Unit]
Description=Product Detective
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/opt/product-detective
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
User=detective

[Install]
WantedBy=multi-user.target
EOF

systemctl enable product-detective
systemctl start product-detective
```

---

## Building Real Training Data

Once you have a running scraper, collect real labelled data:

```bash
# 1. Scrape products
make collect URL="https://www.amazon.in/dp/B0REALPRODUCT"
# Saves to ml/data/raw/

# 2. Label complaint categories (interactive CLI)
make label CSV="ml/data/raw/reviews_B0REALPRODUCT_20250315.csv"
# Walk through each review and assign: 0=overheating, 1=battery, etc.

# 3. Label product-level verdicts
make label-verdicts
# Assign BUY / WAIT / AVOID to each product

# 4. Merge all labelled files
make merge-labels

# 5. Retrain models with real data
make train-real
```

**Target dataset size before real training is worthwhile:**
- Complaint classifier: ≥ 500 labelled reviews (≥50 per category)
- Verdict predictor: ≥ 200 labelled products

---

## Running Tests

```bash
# All tests
make test

# Unit tests only (fast, no DB needed)
make test-unit

# Integration tests (needs MongoDB + Redis running)
make test-integration

# With coverage report
make test-coverage
# Opens htmlcov/index.html
```

---

## Monitoring & Observability

### Health check
```bash
make ping
# Returns: {"status": "healthy", "service": "Product Detective API", ...}
```

### Investigation stats
```bash
curl http://localhost:8000/api/v1/stats | python3 -m json.tool
```

### MongoDB queries
```bash
docker exec -it pd-mongo mongosh product_detective

# Recent investigations
db.investigations.find({}, {case_id:1, verdict:1, product_title:1}).sort({investigated_at:-1}).limit(10)

# Verdict distribution
db.investigations.aggregate([{$group: {_id: "$verdict", count: {$sum: 1}}}])
```

---

## Environment Variables Reference

| Variable                  | Default                     | Description                        |
|---------------------------|-----------------------------|------------------------------------|
| `ENV`                     | `development`               | `development` or `production`      |
| `SECRET_KEY`              | *(required)*                | 64-char random string              |
| `MONGO_URI`               | `mongodb://localhost:27017` | MongoDB connection string          |
| `REDIS_URL`               | `redis://localhost:6379`    | Redis connection string            |
| `SENTIMENT_MODEL`         | `cardiffnlp/...`            | HuggingFace model ID               |
| `MAX_REVIEWS_PER_PRODUCT` | `500`                       | Scraper review limit               |
| `BUY_THRESHOLD`           | `0.68`                      | Composite score for BUY verdict    |
| `WAIT_THRESHOLD`          | `0.44`                      | Composite score for WAIT verdict   |
| `CACHE_TTL`               | `3600`                      | Redis cache TTL in seconds         |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Transformer model fails to load | `pip install torch transformers --upgrade` |
| Selenium can't find Chrome | `apt install chromium chromium-driver` |
| MongoDB connection refused | Ensure MongoDB is running on port 27017 |
| Redis cache unavailable | App continues without cache — Redis is optional |
| Frontend 404 on page refresh | Nginx `try_files` config needed (see above) |
| ML training score is low | Collect more labelled data (see above) |
| Scraper returns captcha error | Add proxy rotation or increase delays |

---

## Future Roadmap

| Feature | Priority | Effort |
|---------|----------|--------|
| Browser extension (Chrome/Firefox) | High | Medium |
| Price history tracking + drop alerts | High | Medium |
| User feedback RLHF loop | Medium | High |
| Real-time review monitoring (webhooks) | Medium | High |
| Multi-language reviews (Hindi, Tamil...) | Medium | High |
| Product comparison mode (A vs B) | Low | Medium |
| Seller reputation scoring | Low | Medium |
| Price prediction model | Low | High |
