# Obsidian Graphs

AI-powered workflow automation for Obsidian vaults using LangGraph and modular nodes. This project provides intelligent agents that can analyze, organize, and enhance your Obsidian knowledge base through automated workflows.

## Features

- **LangGraph Integration** - State-based workflow orchestration for complex document processing
- **Modular Node Architecture** - Extensible agents for different vault operations (article improvement, categorization, cross-referencing, etc.)
- **Dependency Injection** - Clean architecture with protocol-based dependency management
- **FastAPI API** - RESTful endpoints for workflow management and execution
- **Docker Containerization** - Complete development and production environments
- **Comprehensive Testing** - Unit, database, and end-to-end tests with testcontainers
- **Code Quality** - Black formatting, Ruff linting, and automated quality gates

## Quick Start

### 1. Setup Environment

```bash
just setup
```

This installs dependencies with uv and creates `.env` file from `.env.example`.

### 2. Start Development Server

```bash
just up
```

The API will be available at `http://127.0.0.1:8000` (configurable in `.env`).

### 3. Run Tests

```bash
just test
```

Runs unit, database, and end-to-end tests using testcontainers for full isolation.

## Troubleshooting Example: First Workflow Run

This section documents a real-world troubleshooting session to get the first workflow running. It highlights common issues in a containerized environment and how they were resolved.

1.  **`just up-prod` Fails with `unbound variable`**:
    *   **Symptom**: The `just up-prod` command failed with a shell error.
    *   **Root Cause**: The `justfile` was using shell-style `${VAR}` syntax instead of the correct `{{VAR}}` syntax for variable expansion.
    *   **Fix**: Corrected the variable syntax in the `justfile` for all `docker compose` commands.

2.  **`ModuleNotFoundError: No module named 'dev'`**:
    *   **Symptom**: The application container failed to start, with logs showing a `ModuleNotFoundError`.
    *   **Root Cause**: The production Docker image does not include the `dev/` directory, but `src/container.py` was unconditionally importing mock clients from it.
    *   **Fix**: Modified `src/container.py` to conditionally import mock clients only when `USE_MOCK_*` environment variables are set to `true`.

3.  **Celery Worker: `no such table: workflows`**:
    *   **Symptom**: The Celery worker container started but failed immediately when a task was received.
    *   **Root Cause**: The `celery-worker` service was not running database migrations, unlike the `api` service. The `entrypoint.sh` script only ran migrations for `uvicorn` commands.
    *   **Fix**: Updated `entrypoint.sh` to also run migrations when the `celery` command is detected.

4.  **Celery Worker: `POSTGRES_DB: parameter not set`**:
    *   **Symptom**: The Celery worker container failed to start, with an error indicating the `POSTGRES_DB` environment variable was missing.
    *   **Root Cause**: The `celery-worker` service in `docker-compose.yml` was missing the `environment` section that explicitly sets `POSTGRES_DB`.
    *   **Fix**: Added the `environment` section to the `celery-worker` service definition in `docker-compose.yml`.

5.  **GitHub API Error: `403 Not Found` (Repository Name)**:
    *   **Symptom**: The workflow failed with a Git error indicating the repository was not found.
    *   **Root Cause**: An environment variable mismatch. The application expected `OBSIDIAN_VAULT_REPO_FULL_NAME`, but the `.env` file defined `GITHUB_REPO_FULL_NAME`.
    *   **Fix**: Renamed the variable in the `.env` file to match the application's settings.

6.  **GitHub API Error: `403 Forbidden` (Permissions)**:
    *   **Symptom**: After fixing the repository name, the workflow failed again with a permission error.
    *   **Root Cause**: The `GITHUB_PAT` used did not have the necessary `contents: write` permission for the target repository.
    *   **Fix**: The user was instructed to verify the Personal Access Token had the `repo` scope, which grants the required permissions to create branches and open pull requests.

After these fixes, the workflow successfully ran, created a new branch, and opened a pull request.

## API Endpoints

- `GET /` - Hello World
- `GET /health` - Health check
- `POST /api/v1/workflows/` - Create and execute workflows
- `GET /api/v1/workflows/` - List workflow runs
- `GET /api/v1/workflows/{id}` - Get workflow details



## Project Structure

```
src/
├── api/v1/                    # API version 1
│   ├── graph.py               # LangGraph workflow orchestration
│   ├── router.py              # FastAPI route handlers
│   ├── schemas.py             # Pydantic request/response models
│   ├── models/                # Database models
│   ├── nodes/                 # Processing nodes/agents
│   │   ├── article_improvement.py
│   │   ├── category_organization.py
│   │   ├── cross_reference.py
│   │   ├── file_organization.py
│   │   ├── new_article_creation.py
│   │   └── quality_audit.py
│   ├── prompts/               # LLM prompt templates
│   └── tasks/                 # Celery background tasks
│       └── workflow_tasks.py
├── clients/                   # External service integrations
│   └── github_client.py       # GitHub API client
├── container.py               # Dependency injection container
├── db/                        # Database connections and models
│   └── database.py
├── main.py                    # FastAPI application entry point
├── protocols/                 # Abstract interfaces for DI
│   ├── github_client_protocol.py
│   ├── nodes_protocol.py
│   └── vault_protocol.py
├── services/                  # Internal business logic
│   └── vault.py               # Vault file management service
├── settings.py                # Application configuration
├── state.py                   # Shared state definitions
└── tasks/                     # Celery configuration
    └── celery_app.py

tests/
├── unit/                     # Unit tests
│   ├── clients/
│   ├── nodes/
│   ├── services/
│   ├── tasks/
│   └── workflows/
├── db/                       # Database integration tests
└── e2e/                      # End-to-end API tests

dev/
└── mocks/                    # Development mock data
    ├── github_responses.json
    ├── llm_responses.json
    └── vault/

ollama/
└── Dockerfile                # Ollama service container

alembic/                      # Database migrations
```

## Setting Your GitHub Personal Access Token

To enable GitHub repository operations, you need to configure a Personal Access Token (PAT):

1. **Generate a PAT:**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Set an expiration period and select the required scopes

2. **Required Permissions:**
   - `repo` - Full control of private repositories (required for cloning, creating branches, and pull requests)

3. **Configure the Token:**
   - Copy the generated token
   - Open your `.env` file
   - Set `GITHUB_PAT=your_token_here`

**Warning:** Keep your PAT secret and never commit it to version control.

## Environment Variables

Configure in `.env`:

- `PROJECT_NAME` - Project name for Docker volumes (default: obs-graphs)
- `HOST_BIND_IP` - IP to bind (default: 127.0.0.1)
- `HOST_PORT` - Port to bind (default: 8000)
- `DEV_PORT` - Development port (default: 8001)
- `TEST_PORT` - Test port (default: 8002)
- `POSTGRES_HOST` - PostgreSQL host (default: db)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_HOST_DB` - Production database name
- `POSTGRES_DEV_DB` - Development database name
- `POSTGRES_TEST_DB` - Test database name
- `OLLAMA_BASE_URL` - Ollama server base URL (default: http://localhost:11434)
- `OLLAMA_MODEL` - Ollama model to use (default: llama3.2:3b)
- `GITHUB_PAT` - GitHub Personal Access Token for repository operations
- `OBSIDIAN_VAULT_REPO_FULL_NAME` - Target repository (owner/repo format)

## Testing

The project includes three types of tests:

- **Unit Tests**: Fast tests using FastAPI TestClient
- **Database Tests**: PostgreSQL integration tests using testcontainers
- **E2E Tests**: Full stack tests using Docker Compose via testcontainers

All tests run independently without external dependencies.

## Deployment

### Production

```bash
just up-prod
```

Uses production environment configuration from `.env`.

## Docker Architecture

The project uses a sophisticated 5-stage multi-stage Docker build optimized for uv:

### Build Stages

1. **`base`** - Foundation stage with uv installation and dependency files
   - Installs uv package manager
   - Copies `pyproject.toml`, `uv.lock`, and `README.md`
   - Shared base for dependency installation stages

2. **`dev-deps`** - Development dependencies
   - Extends base stage
   - Installs system tools (curl for debugging)
   - Runs `uv sync` to install all dependencies including dev dependencies
   - Creates complete virtual environment for development and testing

3. **`prod-deps`** - Production dependencies only
   - Extends base stage  
   - Runs `uv sync --no-dev` to install only production dependencies
   - Creates lean virtual environment for production

4. **`development`** - Development runtime environment
   - Based on fresh Python 3.12 slim image
   - Installs PostgreSQL client and development tools
   - Creates non-root user for security
   - Copies virtual environment from `dev-deps` stage
   - Includes all application code and development utilities
   - Suitable for local development and CI/CD testing

5. **`production`** - Production runtime environment  
   - Based on fresh Python 3.12 slim image
   - Minimal system dependencies (PostgreSQL client only)
   - Creates non-root user for security
   - Copies lean virtual environment from `prod-deps` stage
   - Includes only necessary application code
   - Optimized for production deployment

### Key Benefits

- **Fast Builds**: uv's speed combined with Docker layer caching
- **Security**: Non-root user execution in runtime stages
- **Optimization**: Separate dev/prod dependency trees
- **Caching**: Aggressive use of Docker build cache for dependencies
- **Minimal Attack Surface**: Production image contains only essential components

### Build Targets

```bash
# Build development image
docker build --target development -t myapp:dev .

# Build production image  
docker build --target production -t myapp:prod .

# Test build (validates production build without keeping image)
just build-test
```

## Adding Database Models

1. Create models in `src/db/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`

Database migrations run automatically in Docker containers.

## Code Quality

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **uv**: Ultra-fast dependency management
- **Pytest**: Testing framework with testcontainers

Run `just format` and `just lint` before committing.

## Volume Management

Project volumes are prefixed with `PROJECT_NAME` to avoid conflicts:

- `${PROJECT_NAME}-postgres-db-prod`: PostgreSQL data persistence
- Volumes are marked as `external: false` for proper cleanup
- Each environment (dev/prod/test) uses separate Docker Compose project names