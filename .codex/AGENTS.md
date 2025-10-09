# Obsidian Graphs - Agent Guide

## Stack
FastAPI + LangGraph + Ollama + PostgreSQL/SQLite + Celery + Redis. Docker orchestration, uv package management, Python 3.12+.

## Architecture
- **DI Container**: `src/container.py` (protocol-based, lazy instantiation)
- **Service Flags**: `.env` controls DB/GitHub/LLM/Redis/ResearchAPI (mock vs real)
- **Submodules**: `obsidian-vault` (content), `ollama-deep-researcher` (research service)

## Configuration & Orchestration
- `.env` = single source of truth for both obs-graphs and research-api
- Compose files:
  - `docker-compose.yml`: base (PostgreSQL, Redis, obs-api, celery-worker, backend network)
  - `docker-compose.research.override.yml`: adds research-api with health check
  - `docker-compose.{dev,test}.override.yml`: environment-specific tweaks
- Dev/test compose commands auto-include research overlay; production excludes it

## Testing
- **Unit Tests (`just unit-test`)**: Single component tests with all dependencies mocked. Fast (<3s). Tests individual classes/functions in isolation.
- **Integration Tests (`just intg-test`)**: Multiple real components working together (workflows, tasks, services). External dependencies mocked. Very fast (~0.2s).
- **E2E Tests (`just e2e-test`)**: Full system in containers (PostgreSQL, Research API, Celery). Slow (~40s+). Tests entire workflow lifecycle via HTTP.
- E2E tests poll `/api/v1/workflows/{id}` until terminal status
- Fixtures wait for container health via `docker compose ps --format json`
- GitHub interactions always mocked in all test types

## DB Migrations
1. Add models in `src/db/models/`
2. `alembic revision --autogenerate -m "description"`
3. `alembic upgrade head`
4. Test on both SQLite and PostgreSQL

## Common Pitfalls
- Check `src/state.py` for correct types (e.g., `FileChange.action: FileAction`)
- Use `git submodule update --init --recursive` after clone
- Never edit submodules directly