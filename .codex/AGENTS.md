# Obsidian Graphs

## 1. Project Overview

This project is an AI-powered workflow automation tool for Obsidian vaults, utilizing LangGraph and modular nodes. It provides automated workflows where intelligent agents analyze, organize, and enhance knowledge bases.

### Key Features
- Article improvement, classification, and cross-referencing
- File organization and quality auditing
- Automatic PR creation for changes

### Technology Stack
- **Framework**: FastAPI
- **Workflow Engine**: LangGraph
- **LLM**: Ollama
- **Database**: PostgreSQL (production), SQLite (testing)
- **Task Queue**: Celery with Redis
- **VCS**: GitPython
- **GitHub API**: PyGithub
- **Containerization**: Docker
- **Package Management**: uv
- **Python Version**: 3.12+

## 2. Architecture and Design

- **Dependency Injection (DI)**: Protocol-based DI container (`src/container.py`)
- **Modular Nodes**: Extensible agent system
- **Service Switching**: Individual flags control each external service (database, GitHub, LLM, Redis)
- **Design Patterns**:
    - **Lazy Instantiation**: Dependencies are created on first access
    - **Settings Pattern**: Configuration management using Pydantic BaseSettings
    - **Repository Pattern**: File operations in vault services

### Service Control Flags

Control each service independently via `.env`:
- `USE_SQLITE` - SQLite/PostgreSQL
- `USE_MOCK_GITHUB` - Mock/Real GitHub
- `USE_MOCK_LLM` - Mock/Real Ollama
- `USE_MOCK_REDIS` - FakeRedis/Real Redis

### Mock Definitions
Define mocks in `dev/mocks/` with appropriate directory structure.

## 3. Coding Conventions

- **Formatter**: `black` (Python 3.12), `ruff` (rules: E, F, I)
    - Ignore `E501` (line too long)
- **Type Hints**: Used throughout the code
- **Naming Conventions**:
    - **Classes**: `PascalCase`
    - **Functions/Methods**: `snake_case`
    - **Constants**: `UPPER_SNAKE_CASE`
    - **Private Attributes**: Prefixed with underscore (e.g., `_github_client`)

### DB Changes
1. Create models in `src/db/models/`
2. Generate migration file: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`
4. Test on both SQLite and PostgreSQL

## 4. Common Mistakes

- **State Objects**: Check `src/state.py` for correct parameter names and types (e.g., `FileChange` uses `action: FileAction`, not `operation: str`)