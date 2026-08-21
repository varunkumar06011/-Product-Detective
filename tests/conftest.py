# conftest.py — shared pytest configuration

import pytest
import asyncio
import sys
import os

# Make backend modules and config importable from tests
# conftest is in tests/, so backend is at ../backend and repo root is at ..
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_repo_root, 'backend'))
sys.path.insert(0, _repo_root)


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# pytest.ini content (embedded here for single-file convenience)
# To use separately, create pytest.ini with the content between the triple quotes:
"""
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
markers =
    unit: Unit tests (fast, no I/O)
    integration: Integration tests (requires FastAPI TestClient)
    slow: Slow tests (network, GPU)
"""
