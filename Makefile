.PHONY: build up down logs clean test lint format type-check coverage help

COMPOSE_FILE := deploy/docker-compose.yml
# Increase timeout for model downloads during build (10-20 minutes)
export COMPOSE_HTTP_TIMEOUT := 1800

# Use a small cross-platform Python helper to check that the Docker
# daemon is available. This avoids shell differences between POSIX,
# cmd.exe, PowerShell, and MSYS environments.
PYTHON ?= python
DOCKER_CHECK = @$(PYTHON) scripts/check_docker.py

# Docker commands
build:
	$(DOCKER_CHECK)
	@echo "🔨 Building Docker images..."
	@echo "⏳ Note: accurate-parser build includes model download (~10-20 min)"
	docker-compose -f $(COMPOSE_FILE) build

build-accurate:
	@echo "🔨 Building accurate-parser (includes model download, ~10-20 min)..."
	docker-compose -f $(COMPOSE_FILE) build accurate-parser

up:
	$(DOCKER_CHECK)
	docker-compose -f $(COMPOSE_FILE) up --build -d

down:
	docker-compose -f $(COMPOSE_FILE) down

logs:
	docker-compose -f $(COMPOSE_FILE) logs -f

# Development commands
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

test-coverage:
	pytest tests/ --cov=src/two_tier_parser --cov-report=html --cov-report=term

lint:
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	@echo "✓ Linting complete"

format:
	black src/ tests/ examples/ --line-length=100
	isort src/ tests/ examples/ --profile=black --line-length=100
	@echo "✓ Formatting complete"

type-check:
	mypy src/two_tier_parser/ --ignore-missing-imports
	@echo "✓ Type checking complete"

coverage: test-coverage
	@echo "Coverage report generated in htmlcov/index.html"

# Cleanup commands
clean:
	@echo "Stopping all containers..."
	docker stop fast-parser accurate-parser 2>/dev/null || true
	docker rm fast-parser accurate-parser 2>/dev/null || true
	docker-compose -f $(COMPOSE_FILE) down -v 2>/dev/null || true
	@echo "Removing all Docker networks..."
	docker network rm document-parser-network 2>/dev/null || true
	@echo "Pruning Docker system (images, containers, networks, volumes, build cache)..."
	docker system prune -a --volumes -f
	@echo "Cleaning Python artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Complete cleanup finished - all Docker resources removed"

# Help
help:
	@echo "Available commands:"
	@echo "  make build          - Build all Docker images (accurate-parser: ~10-20 min)"
	@echo "  make build-accurate - Build only accurate-parser (includes model download)"
	@echo "  make up             - Start services (builds if needed)"
	@echo "  make down           - Stop services"
	@echo "  make logs           - View service logs"
	@echo ""
	@echo "Note: COMPOSE_HTTP_TIMEOUT is set to 1800s (30 min) for model downloads"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make lint           - Run linting checks"
	@echo "  make format         - Format code with Black and isort"
	@echo "  make type-check     - Run type checking with mypy"
	@echo "  make coverage       - Generate coverage report"
	@echo "  make clean          - Clean build artifacts and caches"
	@echo "  make help           - Show this help message"
