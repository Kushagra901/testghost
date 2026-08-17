# ============================================================
#  TestGhost v2 — Makefile
#  Shortcuts for the most common dev tasks
# ============================================================

.PHONY: help install dev-install db-up db-down db-reset migrate \
        run run-proxy lint type-check test test-cov clean

help:
	@echo ""
	@echo "  TestGhost v2 — available commands"
	@echo ""
	@echo "  make install        Install production dependencies"
	@echo "  make dev-install    Install all dependencies including dev"
	@echo "  make db-up          Start PostgreSQL + pgvector in Docker"
	@echo "  make db-down        Stop Docker services"
	@echo "  make db-reset       Drop and recreate the database (destructive)"
	@echo "  make migrate        Run Alembic migrations"
	@echo "  make run            Start the FastAPI backend"
	@echo "  make run-proxy      Start mitmproxy (set SESSION_ID first)"
	@echo "  make lint           Run ruff linter"
	@echo "  make type-check     Run mypy type checker"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage report"
	@echo "  make clean          Remove generated output files"
	@echo ""

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements-dev.txt
	pip install -e .

db-up:
	docker compose up -d
	@echo "Waiting for postgres to be ready..."
	@sleep 3
	@docker compose ps

db-down:
	docker compose down

db-reset:
	docker compose down -v
	docker compose up -d
	@sleep 3
	$(MAKE) migrate

migrate:
	alembic upgrade head

run:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

run-proxy:
	@if [ -z "$(SESSION_ID)" ]; then echo "ERROR: set SESSION_ID=<uuid> before running"; exit 1; fi
	SESSION_ID=$(SESSION_ID) BACKEND_URL=http://localhost:8000 mitmdump -p 8080 -s proxy/addon.py

lint:
	ruff check . --fix

type-check:
	mypy backend ml langgraph_pipeline evaluation generation reporting cli

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

clean:
	rm -rf output/tests/*.py output/reports/*.html
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
