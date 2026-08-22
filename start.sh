#!/bin/bash
cd backend
export PYTHONPATH="/app:/app/backend"
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
