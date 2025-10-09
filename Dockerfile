# syntax=docker/dockerfile:1.7-labs
# ==============================================================================
# Stage 1: Base
# - Base stage with uv setup and dependency files
# ==============================================================================
FROM python:3.12-slim as base

WORKDIR /app

# Install uv
RUN --mount=type=cache,target=/root/.cache \
  pip install uv

# Copy dependency definition files  
COPY pyproject.toml uv.lock README.md ./


# ==============================================================================
# Stage 2: Dev Dependencies
# - Installs ALL dependencies (including development) to create a cached layer
#   that can be leveraged by CI/CD for linting, testing, etc.
# ==============================================================================
FROM base as dev-deps

# Install system dependencies required for the application
# - curl: used for debugging in the development container
# - git: required for git dependencies
RUN apt-get update && apt-get install -y curl git && rm -rf /var/lib/apt/lists/*

# Install all dependencies, including development ones
# Use OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN for private git dependencies
ARG OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN
RUN --mount=type=cache,target=/root/.cache \
  if [ -n "$OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN" ]; then \
  git config --global url."https://${OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; \
  fi && \
  uv sync && \
  git config --global --unset url."https://${OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN}@github.com/".insteadOf || true


# ==============================================================================
# Stage 3: Production Dependencies
# - Creates a lean virtual environment with only production dependencies.
# ==============================================================================
FROM base as prod-deps

# Install git for git dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install only production dependencies
# Use OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN for private git dependencies
ARG OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN
RUN --mount=type=cache,target=/root/.cache \
  if [ -n "$OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN" ]; then \
  git config --global url."https://${OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"; \
  fi && \
  uv sync --no-dev && \
  git config --global --unset url."https://${OLLAMA_DEEP_RESEARCHER_GITHUB_TOKEN}@github.com/".insteadOf || true



# ==============================================================================
# Stage 4: Application Code
# - Copies application code and initializes submodules
# ==============================================================================
FROM python:3.12-slim AS app-code

# Install git for submodules
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

# Copy application code and submodules
COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup submodules/ ./submodules
COPY --chown=appuser:appgroup pyproject.toml .
COPY --chown=appuser:appgroup entrypoint.sh .

# Initialize submodules if .git exists
RUN if [ -d .git ]; then git submodule update --init --recursive; fi

RUN chmod +x entrypoint.sh

USER appuser


# ==============================================================================
# Stage 5: Development
# - Development environment with all dependencies and debugging tools
# - Includes curl and other development utilities
# ==============================================================================
FROM python:3.12-slim AS development

# Install PostgreSQL client and development tools
RUN apt-get update && apt-get install -y postgresql-client curl git && rm -rf /var/lib/apt/lists/*

# Create a non-root user for development
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

# Copy the development virtual environment from dev-deps stage
COPY --from=dev-deps /app/.venv ./.venv

# Set the PATH to include the venv's bin directory
ENV PATH="/app/.venv/bin:${PATH}"

# Copy application code from app-code stage
COPY --from=app-code --chown=appuser:appgroup /app ./

# Copy tests for development
COPY --chown=appuser:appgroup tests/ ./tests

# Switch to non-root user
USER appuser

EXPOSE 8000

# Development healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else sys.exit(1)"

ENTRYPOINT ["/app/entrypoint.sh"]



# ==============================================================================
# Stage 6: Production
# - Creates the final, lightweight production image.
# - Copies the lean venv and only necessary application files.
# ==============================================================================
FROM python:3.12-slim AS production

# Install PostgreSQL client for database operations
RUN apt-get update && apt-get install -y postgresql-client git && rm -rf /var/lib/apt/lists/*



# Create a non-root user and group for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

# Set the working directory
WORKDIR /app

# Grant ownership of the working directory to the non-root user
RUN chown appuser:appgroup /app

# Copy the lean virtual environment from the prod-deps stage
COPY --from=prod-deps /app/.venv ./.venv

# Set the PATH to include the venv's bin directory for simpler command execution
ENV PATH="/app/.venv/bin:${PATH}"

# Copy application code from app-code stage
COPY --from=app-code --chown=appuser:appgroup /app ./

# Switch to the non-root user
USER appuser

# Expose the port the app runs on (will be mapped by Docker Compose)
EXPOSE 8000

# Healthcheck using only Python's standard library to avoid extra dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').getcode() == 200 else sys.exit(1)"

# Set the entrypoint script to be executed when the container starts
ENTRYPOINT ["/app/entrypoint.sh"]
