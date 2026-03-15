# Product Detective — Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for lxml + Selenium Chrome
RUN apt-get update && apt-get install -y \
    gcc g++ \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install Python deps
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download sentiment model (cached into image)
RUN python -c "from transformers import pipeline; pipeline('sentiment-analysis', model='cardiffnlp/twitter-roberta-base-sentiment-latest')" || true

COPY backend/ .
COPY config/ config/
COPY ml/ ml/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
