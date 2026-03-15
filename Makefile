# Product Detective — Developer Makefile
# Usage: make <target>

.PHONY: help install dev test test-unit test-integration lint train clean docker-up docker-down

PYTHON   := python3
PIP      := pip3
NODE     := node
NPM      := npm
PYTEST   := pytest
UVICORN  := uvicorn

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  🔍 PRODUCT DETECTIVE — Developer Commands"
	@echo ""
	@echo "  Setup"
	@echo "    make install          Install all dependencies (backend + frontend)"
	@echo "    make install-backend  Install Python dependencies only"
	@echo "    make install-frontend Install Node dependencies only"
	@echo ""
	@echo "  Development"
	@echo "    make dev              Start both backend and frontend (hot-reload)"
	@echo "    make dev-backend      Start FastAPI backend only (port 8000)"
	@echo "    make dev-frontend     Start React frontend only  (port 3000)"
	@echo ""
	@echo "  Testing"
	@echo "    make test             Run all tests"
	@echo "    make test-unit        Run unit tests only"
	@echo "    make test-integration Run integration tests (requires MongoDB + Redis)"
	@echo "    make test-coverage    Run tests with HTML coverage report"
	@echo ""
	@echo "  Code Quality"
	@echo "    make lint             Lint backend (ruff) and frontend (eslint)"
	@echo "    make format           Auto-format backend code (ruff)"
	@echo ""
	@echo "  ML Pipeline"
	@echo "    make train            Train all ML models (synthetic data)"
	@echo "    make train-real       Train with real labelled data"
	@echo "    make collect URL=...  Scrape and save a product"
	@echo "    make label CSV=...    Label complaints interactively"
	@echo ""
	@echo "  Docker"
	@echo "    make docker-up        Start full stack with Docker Compose"
	@echo "    make docker-down      Stop all containers"
	@echo "    make docker-rebuild   Rebuild and restart containers"
	@echo "    make docker-logs      Tail all container logs"
	@echo ""
	@echo "  Utilities"
	@echo "    make clean            Remove build artifacts and caches"
	@echo "    make shell            Open backend Python REPL with app context"
	@echo ""

# ── Installation ───────────────────────────────────────────────────────────────
install: install-backend install-frontend
	@echo "✅ All dependencies installed"

install-backend:
	@echo "→ Installing Python dependencies..."
	cd backend && $(PIP) install -r requirements.txt
	@echo "✅ Backend dependencies installed"

install-frontend:
	@echo "→ Installing Node dependencies..."
	cd frontend && $(NPM) install
	@echo "✅ Frontend dependencies installed"

# ── Development Servers ────────────────────────────────────────────────────────
dev:
	@echo "→ Starting Product Detective (full stack)..."
	@make docker-up

dev-backend:
	@echo "→ Starting FastAPI backend on http://localhost:8000"
	@echo "→ API docs: http://localhost:8000/api/docs"
	cd backend && $(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "→ Starting React frontend on http://localhost:3000"
	cd frontend && $(NPM) run dev

# ── Testing ────────────────────────────────────────────────────────────────────
test: test-unit test-integration
	@echo "✅ All tests passed"

test-unit:
	@echo "→ Running unit tests..."
	PYTHONPATH=backend $(PYTEST) tests/unit/ -v --tb=short

test-integration:
	@echo "→ Running integration tests..."
	PYTHONPATH=backend $(PYTEST) tests/integration/ -v --tb=short

test-coverage:
	@echo "→ Running tests with coverage..."
	PYTHONPATH=backend $(PYTEST) tests/ -v \
		--cov=backend/modules \
		--cov=backend/api \
		--cov-report=html:htmlcov \
		--cov-report=term-missing
	@echo "→ Coverage report: htmlcov/index.html"

test-watch:
	@echo "→ Running tests in watch mode..."
	PYTHONPATH=backend $(PYTEST) tests/unit/ -v --tb=short -f

# ── Code Quality ───────────────────────────────────────────────────────────────
lint:
	@echo "→ Linting backend..."
	cd backend && ruff check . --select=E,F,W,I || true
	@echo "→ Linting frontend..."
	cd frontend && $(NPM) run lint || true

format:
	@echo "→ Formatting backend..."
	cd backend && ruff format .
	@echo "✅ Backend formatted"

# ── ML Pipeline ────────────────────────────────────────────────────────────────
train:
	@echo "→ Training ML models (synthetic data)..."
	PYTHONPATH=backend $(PYTHON) ml/training/train_pipeline.py --mode all
	@echo "✅ Models saved to ml/saved_models/"

train-real:
	@echo "→ Training ML models (real data)..."
	PYTHONPATH=backend $(PYTHON) ml/training/train_pipeline.py \
		--mode all \
		--complaint-data ml/data/complaint_labels.csv \
		--verdict-data ml/data/verdict_labels.csv

collect:
	@echo "→ Collecting product data from: $(URL)"
	PYTHONPATH=backend $(PYTHON) scripts/collect_data.py collect \
		--url "$(URL)" --out ml/data/raw/

label:
	@echo "→ Opening complaint labelling tool..."
	PYTHONPATH=backend $(PYTHON) scripts/collect_data.py label \
		--input "$(CSV)" --out ml/data/labelled/

label-verdicts:
	@echo "→ Opening verdict labelling tool..."
	PYTHONPATH=backend $(PYTHON) scripts/collect_data.py label-verdicts \
		--input ml/data/raw/ --out ml/data/labelled/

merge-labels:
	@echo "→ Merging labelled data..."
	PYTHONPATH=backend $(PYTHON) scripts/collect_data.py merge \
		--input ml/data/labelled/ --out ml/data/

notebook:
	@echo "→ Starting Jupyter notebook..."
	cd ml/notebooks && jupyter notebook exploration.ipynb

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-up:
	@echo "→ Starting Docker Compose stack..."
	docker compose up -d
	@echo "✅ Stack running:"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   Backend:   http://localhost:8000"
	@echo "   API Docs:  http://localhost:8000/api/docs"
	@echo "   MongoDB:   localhost:27017"
	@echo "   Redis:     localhost:6379"

docker-down:
	@echo "→ Stopping containers..."
	docker compose down

docker-rebuild:
	@echo "→ Rebuilding and restarting..."
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "✅ Rebuilt and running"

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

# ── Utilities ──────────────────────────────────────────────────────────────────
clean:
	@echo "→ Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f .coverage coverage.xml
	cd frontend && rm -rf dist node_modules/.cache 2>/dev/null || true
	@echo "✅ Clean"

shell:
	@echo "→ Opening Python shell with app context..."
	cd backend && PYTHONPATH=. $(PYTHON) -c "from main import app; import IPython; IPython.embed()"

# ── Quick health check ─────────────────────────────────────────────────────────
ping:
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool || echo "Backend not running"
