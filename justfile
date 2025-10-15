# ==============================================================================
# justfile for FastAPI Project Automation
# ==============================================================================

set dotenv-load

PROJECT_NAME := env("PROJECT_NAME", "obs-glx")
POSTGRES_IMAGE := env("POSTGRES_IMAGE", "postgres:16-alpine")

DEV_PROJECT_NAME := PROJECT_NAME + "-dev"
PROD_PROJECT_NAME := PROJECT_NAME + "-prod"
TEST_PROJECT_NAME := PROJECT_NAME + "-test"

# Production uses only base compose
PROD_COMPOSE := "docker compose -f docker-compose.yml --project-name " + PROD_PROJECT_NAME

# Development and test use environment-specific overlays
DEV_COMPOSE  := "docker compose -f docker-compose.yml -f docker-compose.dev.override.yml --project-name " + DEV_PROJECT_NAME
TEST_COMPOSE := "docker compose -f docker-compose.yml -f docker-compose.test.override.yml --project-name " + TEST_PROJECT_NAME

# default target
default: help

# Show available recipes
help:
    @echo "Usage: just [recipe]"
    @echo "Available recipes:"
    @just --list | tail -n +2 | awk '{printf "  \033[36m%-20s\033[0m %s\n", $1, substr($0, index($0, $2))}'
# ==============================================================================
# Environment Setup
# ==============================================================================

# Initialize project: install dependencies, create .env file and pull required Docker images
setup:
    @echo "🐍 Installing python dependencies with uv..."
    @uv sync
    @echo "📦 Initializing and updating git submodules..."
    @git submodule update --init --recursive
    @echo "Creating environment file..."
    @if [ ! -f .env ] && [ -f .env.example ]; then \
        echo "Creating .env from .env.example..."; \
        cp .env.example .env; \
        echo "✅ Environment file created (.env)"; \
    else \
        echo ".env already exists. Skipping creation."; \
    fi
    @echo "💡 You can customize .env for your specific needs:"
    @echo "   📝 Adjust other settings as needed"
    @echo ""
    @echo "Pulling PostgreSQL image for tests..."
    docker pull {{POSTGRES_IMAGE}}
    @echo "✅ Setup complete. Dependencies are installed and .env file is ready."

# ==============================================================================
# Development Environment Commands
# ==============================================================================

# Start all development containers in detached mode
up:
    @echo "Starting up development services..."
    @{{DEV_COMPOSE}} up -d

# Stop and remove all development containers
down:
    @echo "Shutting down development services..."
    @{{DEV_COMPOSE}} down --remove-orphans

# Start all production-like containers
up-prod:
    @echo "Starting up production-like services..."
    @{{PROD_COMPOSE}} up -d --build --pull always --remove-orphans

# Stop and remove all production-like containers
down-prod:
    @echo "Shutting down production-like services..."
    @{{PROD_COMPOSE}} down --remove-orphans

# Rebuild and restart API container only
rebuild:
    @echo "Rebuilding and restarting API service..."
    @{{DEV_COMPOSE}} down --remove-orphans
    @{{DEV_COMPOSE}} build --no-cache

# Tail logs from all development services
logs:
    @echo "Tailing logs from all development services..."
    @{{DEV_COMPOSE}} logs -f

# Tail logs from specific service
logs-service SERVICE:
    @echo "Tailing logs from {{SERVICE}}..."
    @{{DEV_COMPOSE}} logs -f {{SERVICE}}

# ==============================================================================
# TESTING
# ==============================================================================

# Run complete test suite
test: 
  @just local-test 
  @just docker-test

# Run lightweight local test suite
local-test:
    @just unit-test
    @just sdk-test
    @just intg-test
    @just sqlt-test

# Run unit tests locally
unit-test:
    @echo "🚀 Running unit tests..."
    @uv run --extra sdk pytest tests/unit

# Run SDK tests locally
sdk-test:
    @echo "🚀 Running SDK tests..."
    @uv run --extra sdk pytest tests/sdk

# Run integration tests locally
intg-test:
    @echo "🚀 Running integration tests..."
    @uv run pytest tests/intg

# Run database tests with SQLite
sqlt-test:
    @echo "🚀 Running database tests with SQLite..."
    @OBS_GLX_USE_SQLITE=true uv run pytest tests/db

# Run all Docker-based tests
docker-test:
  @just build-test
  @just psql-test
  @just e2e-test

# Build Docker image for testing without leaving artifacts
build-test:
    @echo "Building Docker image for testing..."
    @API_TAG=$(date +%s)-api-build-test; \
    WORKER_TAG=$(date +%s)-worker-build-test; \
    DOCKER_BUILDKIT=1 docker build --target production --tag temp-api-build-test:$API_TAG --secret id=github_token,env=OBS_GRAPHS_TOKEN -f Dockerfile . && \
    DOCKER_BUILDKIT=1 docker build --target production --tag temp-worker-build-test:$WORKER_TAG --secret id=github_token,env=OBS_GRAPHS_TOKEN -f worker/obs_glx_worker/Dockerfile . && \
    echo "Build successful. Cleaning up temporary images..." && \
    docker rmi temp-api-build-test:$API_TAG temp-worker-build-test:$WORKER_TAG || true

# Run database tests with PostgreSQL
psql-test:
    @echo "🚀 Starting TEST containers for PostgreSQL database test..."
    @OBS_GLX_USE_SQLITE=false {{TEST_COMPOSE}} up -d --build
    @echo "Waiting for database to be ready..."
    @OBS_GLX_USE_SQLITE=false {{TEST_COMPOSE}} exec obs-glx-api sh -c "while ! pg_isready -h db -U ${POSTGRES_USER} -d ${POSTGRES_TEST_DB}; do echo 'Waiting for database...'; sleep 2; done"
    @echo "Running migrations..."
    @OBS_GLX_USE_SQLITE=false {{TEST_COMPOSE}} exec obs-glx-api alembic upgrade head
    @echo "Running database tests inside api container (against PostgreSQL)..."
    @OBS_GLX_USE_SQLITE=false {{TEST_COMPOSE}} exec obs-glx-api pytest tests/db; \
    EXIT_CODE=$?; \
    echo "🔴 Stopping TEST containers..."; \
    {{TEST_COMPOSE}} down --remove-orphans; \
    exit $EXIT_CODE

# Run e2e tests against containerized application stack
e2e-test:
    @echo "🚀 Running e2e tests..."
    @OBS_GLX_USE_SQLITE=false uv run pytest tests/e2e

# ==============================================================================
# CODE QUALITY
# ==============================================================================

# Format code with black and ruff --fix
format:
    @echo "Formatting code with black and ruff..."
    @uv run black .
    @uv run ruff check . --fix

# Lint code with black check and ruff
lint:
    @echo "Linting code with black check and ruff..."
    @uv run black --check .
    @uv run ruff check .
    
# ==============================================================================
# CLEANUP
# ==============================================================================

# Remove __pycache__ and .venv to make project lightweight
clean:
    @echo "🧹 Cleaning up project..."
    @find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    @rm -rf .venv
    @rm -rf .pytest_cache
    @rm -rf .ruff_cache
    @rm -rf .uv-cache
    @rm -f test_db.sqlite3
    @echo "✅ Cleanup completed"
