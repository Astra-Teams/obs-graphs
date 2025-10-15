# syntax=docker/dockerfile:1.7-labs
# ==============================================================================
# Stage 1: Base image with uv and git tooling
# ==============================================================================
FROM python:3.12-slim as base

WORKDIR /app

# Install uv and git (required for private dependencies)
RUN --mount=type=cache,target=/root/.cache \
  pip install uv && \
  apt-get update && apt-get install -y git openssh-client && rm -rf /var/lib/apt/lists/*

# Copy dependency definition files for uv to resolve
COPY pyproject.toml uv.lock ./


# ==============================================================================
# Stage 2: Development dependencies (full set including dev extras)
# ==============================================================================
FROM base as dev-deps

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache \
  --mount=type=secret,id=github_token \
  if [ -s /run/secrets/github_token ]; then \
  git config --global credential.helper store && \
  printf "https://oauth2:%s@github.com\n" "$(cat /run/secrets/github_token)" > ~/.git-credentials; \
  fi && \
  uv sync


# ==============================================================================
# Stage 3: Production dependencies (lean virtualenv)
# ==============================================================================
FROM base as prod-deps

RUN --mount=type=cache,target=/root/.cache \
  --mount=type=secret,id=github_token \
  if [ -s /run/secrets/github_token ]; then \
  git config --global credential.helper store && \
  printf "https://oauth2:%s@github.com" "$(cat /run/secrets/github_token)" > ~/.git-credentials; \
  fi && \
  uv sync --no-dev


# ==============================================================================
# Stage 4: Application code (shared between dev/prod images)
# ==============================================================================
FROM base as app-code

RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

RUN --mount=type=secret,id=github_token \
  if [ -s /run/secrets/github_token ]; then \
  git config --global credential.helper store && \
  printf "https://oauth2:%s@github.com" "$(cat /run/secrets/github_token)" > ~/.git-credentials; \
  fi

COPY --chown=appuser:appgroup src/ ./src
COPY --chown=appuser:appgroup worker/ ./worker
COPY --chown=appuser:appgroup alembic/ ./alembic
COPY --chown=appuser:appgroup submodules/obsidian-vault/ ./submodules/obsidian-vault/
COPY --chown=appuser:appgroup pyproject.toml ./

RUN if [ -d .git ]; then git submodule update --init --recursive && chown -R appuser:appgroup .; fi

USER appuser


# ==============================================================================
# Stage 5: Development target
# ==============================================================================
FROM base as development

RUN apt-get update && apt-get install -y postgresql-client curl && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

COPY --from=dev-deps /app/.venv ./.venv

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app"

COPY --from=app-code --chown=appuser:appgroup /app ./
COPY --chown=appuser:appgroup tests/ ./tests
COPY --chown=appuser:appgroup dev/ ./dev

USER appuser

ENTRYPOINT ["python", "-m", "celery"]
CMD ["-A", "worker.obs_graphs_worker.app", "worker", "--loglevel=debug"]


# ==============================================================================
# Stage 6: Production target
# ==============================================================================
FROM base as production

RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup -d /home/appuser -m appuser

WORKDIR /app
RUN chown appuser:appgroup /app

COPY --from=prod-deps /app/.venv ./.venv

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH="/app"

COPY --from=app-code --chown=appuser:appgroup /app ./

USER appuser

ENTRYPOINT ["python", "-m", "celery"]
CMD ["-A", "worker.obs_graphs_worker.app", "worker", "--loglevel=info"]
