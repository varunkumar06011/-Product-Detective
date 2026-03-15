#!/bin/bash
# Product Detective — Production Startup Script for Render

# Install chromium if not present (Render handles this via builds, but safety check)
# apt-get update && apt-get install -y chromium chromium-driver

# Run migrations or training if needed (Optional)
# python ml/training/train_pipeline.py --mode all

# Start Uvicorn
# --proxy-headers: Required for running behind a reverse proxy like Render
# --forwarded-allow-ips='*': Required for correct client IP detection
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/backend
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --proxy-headers \
    --forwarded-allow-ips='*'
