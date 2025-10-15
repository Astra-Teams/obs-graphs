## 🚀 Overview

**Obsidian Graphs** is an AI-driven workflow automation service for Obsidian. It uses modular **LangGraph agents** to analyze and enhance knowledge bases, submitting changes by delegating draft branches to the **obs-gtwy** gateway service.

**Core Tech**: FastAPI, LangGraph, stl-conn (Stella Connector), PostgreSQL/SQLite, Celery, Redis, Docker.

---

## 📂 Repository Structure

-   `src/obs_graphs/`: Main application source.
-   `tests/`: Test suite (Unit, Integration, E2E, DB).
-   `dev/`: Mock clients and responses for offline development.
-   `submodules/`: Git submodules for dependencies like `constellations`.
-   `sdk/`: First-party Python SDK mirroring the `starprobe` structure for workflow execution.
-   `alembic/`: Database migrations.
-   `docker-compose*.yml`: Container orchestration files.
-   `justfile`: Task runner for automation.
-   `.codex/`: Development documentation.

---

## 🏛️ Core Architecture

### 1. Application Core (`src/obs_graphs/`)
-   **API (`api/`)**: FastAPI endpoints with path-based workflow type routing (`/api/workflows/{workflow_type}/run`), Pydantic schemas for validation.
-   **Workflow Engine (`graphs/`)**:
    -   Factory pattern (`factory.py`) for extensible workflow graph creation with dependency injection
    -   Protocol interface (`protocol.py`) defining `WorkflowGraphProtocol` for type-safe graph implementations
    -   LangGraph state machines for stateful workflow orchestration using modular agent nodes
    -   Pydantic-based GraphState with runtime validation and WorkflowStatus enum for robust state management
    -   Currently supports: `article-proposal` workflow type
-   **Services (`services/`)**: Business logic, including `Vault Service` for file operations.
-   **Data Access (`db/`)**: SQLAlchemy models with `workflow_type` column and repository pattern for DB interactions.
-   **Clients (`clients/`)**: LLM integration via `stl-conn` SDK (`StlConnClient`, `MockStlConnClient`) implementing `StlConnClientProtocol`; gateway and research integrations consume shared `obs_gtwy_sdk` and `starprobe_sdk` packages.
-   **SDK (`sdk/obs_graphs_sdk/`)**: First-party workflow client packaged as an optional dependency and aligned with the `starprobe` SDK conventions.
-   **Async Tasks (`worker/obs_graphs_worker/`)**: Background task execution with Redis, uses factory pattern for workflow type resolution.
-   **Configuration (`config/`)**: Environment-based settings for stl-conn endpoint (`stl_conn_settings.py`), database, Redis, gateway, and research API configurations.
-   **DI (`dependencies.py`)**: FastAPI-native dependency injection hub with provider functions for services, clients, and configuration. LLM client creation delegated to stl-conn SDK.
-   **Protocols (`protocols/`)**: Interface contracts for type-safe interactions. Uses `StlConnClientProtocol` from stl-conn SDK for LLM operations.

### 2. Testing (`tests/`)
-   **Unit**: Isolated component tests (fast) - all services mocked.
-   **SDK**: Tests for the exported `obs_graphs_sdk` package with HTTP access patched out.
-   **Integration**: Multi-component interaction tests - all services mocked.
-   **E2E**: Full system tests in a containerized environment (slow) - uses real Redis for Celery testing.
-   **Database**: Migration and data integrity validation.
-   **Environment Configuration**: Each test category has its own environment setup in `tests/envs.py`, applied via `conftest.py` in each test directory.

---

## ⚖️ Architectural Principles

-   **Separation of Concerns**: Clear boundaries between API, business logic, data, and infrastructure.
-   **Dependency Injection**: FastAPI-native DI using `Depends()` for testability and flexibility. Provider functions in `dependencies.py` create services with appropriate configurations. LLM backend selection delegated to stl-conn service.
-   **Schema Separation**: Pydantic for API validation, distinct types for internal state. GraphState uses Pydantic BaseModel with runtime validation for robust state management.
-   **Node-Based Agents**: Modular, single-responsibility agents with constructor injection of dependencies.
-   **Comprehensive Testing**: Multi-layered testing strategy (Unit → Integration → E2E) with easy mocking via `app.dependency_overrides`.

---

## 🛠️ Development Workflow

1.  **Setup**: Use `just setup` and `just up` to start the local stack.
2.  **Testing**: Run tests with `just unit-test` and `just intg-test`.
4.  **Graph Extension**:
    -   Implement the `NodeProtocol`.
    -   Define Pydantic schemas for state validation.
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

---

## 📦 Submodules

This project uses Git submodules to manage external dependencies. Submodules are located in the `submodules/` directory and should never be edited directly. If changes are required, please contact the respective repository maintainers or request updates from the user.

### constellations (submodules/constellations)
Provides the Obsidian Vault structure and utilities for managing knowledge bases, handling file operations, vault organization, and integration with Obsidian's markdown-based knowledge management system.

### starprobe (submodules/starprobe)
Implements AI-driven research workflows, document analysis, and content generation using LangGraph agents as a research and document generation service.

### stl-conn (submodules/stl-conn)
Provides a unified interface for connecting to various Large Language Models, handling authentication, and managing API interactions as the Stella Connector for LLM integration.

### obs-gtwy (submodules/obs-gtwy)
Acts as a bridge between the Obsidian Graphs service and external systems, handling draft branch submissions and workflow delegations as the gateway service for Obsidian integrations.

---
