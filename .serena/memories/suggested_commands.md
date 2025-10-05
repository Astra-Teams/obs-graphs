# Suggested Commands

## Setup
- `just setup` - Install dependencies with uv and create .env from .env.example

## Development
- `just up` - Start development containers
- `just down` - Stop development containers
- `just rebuild` - Rebuild and restart API container

## Code Quality
- `just format` - Format code with black and ruff --fix
- `just lint` - Lint code with black --check and ruff

## Testing
- `just test` - Run complete test suite (local + docker)
- `just local-test` - Run unit tests + SQLite DB tests
- `just unit-test` - Run unit tests only
- `just sqlt-test` - Run DB tests with SQLite
- `just docker-test` - Run all Docker-based tests
- `just pstg-test` - Run DB tests with PostgreSQL
- `just e2e-test` - Run end-to-end tests
- `just build-test` - Test Docker build without keeping artifacts

## Production
- `just up-prod` - Start production-like containers
- `just down-prod` - Stop production containers

## Cleanup
- `just clean` - Remove __pycache__, .venv, cache directories

## Database Migrations
- `alembic revision --autogenerate -m "description"` - Generate migration
- `alembic upgrade head` - Apply migrations

## System Commands (macOS Darwin)
Standard Unix commands work on Darwin: git, ls, cd, grep, find, cat, etc.
