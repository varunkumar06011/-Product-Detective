FROM python:3.11-slim

# Install system dependencies:
# - gcc/g++: compiling Python packages (lxml, etc.)
# - libxml2/libxslt: for BeautifulSoup lxml parser
# - chromium + chromium-driver: for Selenium headless scraping
# - fonts: so Chromium renders pages properly
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libxml2-dev libxslt1-dev zlib1g-dev \
    chromium chromium-driver \
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Tell Selenium where Chromium is
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Copy requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the full project
COPY . .

# Set PYTHONPATH so config/ and backend/ are importable
ENV PYTHONPATH="/app:/app/backend"

# Render sets the PORT env var
EXPOSE $PORT

# Start the backend
CMD cd backend && python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'
