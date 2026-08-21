# Product Detective — ML Training Dockerfile
# Used by the ml-trainer service in docker-compose.yml (training profile)
FROM python:3.11-slim

WORKDIR /app

# System deps for scikit-learn / scipy
RUN apt-get update && apt-get install -y \
    gcc g++ \
    && rm -rf /var/lib/apt/lists/*

# Install ML dependencies
RUN pip install --no-cache-dir \
    scikit-learn>=1.0.0 \
    scipy>=1.7.0 \
    numpy>=1.20.0 \
    pandas>=1.3.0 \
    joblib>=1.1.0

# Copy training code
COPY training/ training/

# Default command (overridden by docker-compose)
CMD ["python", "training/train_pipeline.py", "--mode", "all"]
