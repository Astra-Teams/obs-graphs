# AGENTS.md - AI Agent Context Document

## 🚀 Overview

**Obsidian Graphs** is an AI-driven workflow automation service for Obsidian. It uses modular **LangGraph agents** to analyze and enhance knowledge bases, submitting changes by delegating draft branches to the **obs-gtwy** gateway service.

**Core Tech**: FastAPI, LangGraph, Ollama, PostgreSQL/SQLite, Celery, Redis, Docker.

---

## 📂 Repository Structure

-   `src/obs_graphs/`: Main application source.
-   `tests/`: Test suite (Unit, Integration, E2E, DB).
-   `dev/`: Mock clients and responses for offline development.
-   `submodules/`: Git submodules for dependencies like `obsidian-vault`.
-   `alembic/`: Database migrations.
-   `docker-compose*.yml`: Container orchestration files.
-   `justfile`: Task runner for automation.
-   `.codex/`: Development documentation.

---

## 🏛️ Core Architecture

### 1. Application Core (`src/obs_graphs/`)
-   **API (`api/`)**: FastAPI endpoints, Pydantic schemas, and routing.
-   **Workflow Engine (`graphs/`)**: LangGraph for stateful workflow orchestration using modular agent nodes.
-   **Services (`services/`)**: Business logic, including `Vault Service` for file operations.
-   **Data Access (`db/`)**: SQLAlchemy models and repository pattern for DB interactions.
-   **Clients (`clients/`)**: External service clients (obs-gtwy gateway, Research APIs) plus unified LLM adapters (`OllamaClient`, `MLXClient`) behind `LLMClientProtocol`.
-   **Async Tasks (`celery/`)**: Background task execution with Redis.
-   **Configuration (`config/`)**: Environment-based settings and feature flags (e.g., `OBS_GRAPHS_LLM_BACKEND`). Backend-specific parameters live in `src/obs_graphs/config/ollama_settings.py` and `src/obs_graphs/config/mlx_settings.py`.
-   **DI (`container.py`)**: Protocol-based Dependency Injection for loose coupling.
-   **Protocols (`protocols/`)**: Interface contracts for type-safe interactions.

### 2. Testing (`tests/`)
-   **Unit**: Isolated component tests (fast) - all services mocked.
-   **Integration**: Multi-component interaction tests - all services mocked.
-   **E2E**: Full system tests in a containerized environment (slow) - uses real Redis for Celery testing.
-   **Database**: Migration and data integrity validation.
-   **Environment Configuration**: Each test category has its own environment setup in `tests/envs.py`, applied via `conftest.py` in each test directory.

---

## ⚖️ Architectural Principles

-   **Separation of Concerns**: Clear boundaries between API, business logic, data, and infrastructure.
-   **Dependency Injection**: Protocol-based DI for testability and flexibility; container resolves LLM backend per request.
-   **Schema Separation**: Pydantic for API validation, distinct types for internal state.
-   **Node-Based Agents**: Modular, single-responsibility agents registered by name.
-   **Comprehensive Testing**: Multi-layered testing strategy (Unit → Integration → E2E).

---

## 🛠️ Development Workflow

1.  **Setup**: Use `just setup` and `just up` to start the local stack.
2.  **Testing**: Run tests with `just unit-test` and `just intg-test`.
3.  **Graph Extension**:
    -   Implement the `NodeProtocol`.
    -   Define Pydantic schemas.
    -   Build the LangGraph state machine.
    -   Integrate with the API and add tests.
4.  **DB Changes**:
    -   Update SQLAlchemy models.
    -   Generate migrations with `alembic`.
    -   Test migrations on both SQLite and PostgreSQL.

---

## ⚙️ Configuration & QA

-   **Configuration**: Managed via `.env` files and Docker Compose overrides for different environments.
-   **Quality Assurance**: Enforced through type hints (mypy), linting/formatting (Ruff), and a CI/CD pipeline that runs all automated tests and security scans.
