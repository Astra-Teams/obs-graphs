# Obsidian Graphs

Obsidian Graphs is an AI-powered workflow automation service for Obsidian vaults. It orchestrates modular LangGraph agents that can analyse, organise, and enhance a knowledge base by proposing and applying changes through obs-gtwy managed draft branches.

## What's in the box?

- **FastAPI** application that exposes workflow orchestration endpoints.
- **LangGraph** powered agents for article improvements, classification, cross-referencing, and vault quality audits.
- **Pydantic `BaseSettings` configuration** with dedicated modules for database, Redis, and research API settings.
- **Pluggable LLM backends** (Ollama or MLX) with a unified client protocol for agent prompts.
- **Git submodules** for external integrations, including the shared Obsidian vault checkout and the reference deep-research API.

## Directory Structure

```
├── src/obs_graphs/       # Main application package
│   ├── api/             # FastAPI endpoints and schemas
│   ├── celery/          # Celery tasks for async workflow execution
│   ├── clients/         # External service clients (obs-gtwy, research API, LLM adapters)
│   ├── config/          # Configuration modules
│   ├── container.py     # Dependency injection container
│   ├── db/              # Database models and session management
│   ├── graphs/          # LangGraph workflow definitions
│   │   └── article_proposal/  # Article proposal workflow
│   ├── protocols/       # Protocol definitions for dependency injection
│   ├── services/        # Business logic services
│   ├── settings.py      # Application settings
│   └── main.py          # FastAPI application entry point
├── tests/               # Unit, database, and end-to-end tests
├── dev/                 # Development fixtures and mocks
├── submodules/          # Git submodules for external dependencies
│   ├── obsidian-vault/              # Local checkout of the vault used during workflows
│   └── olm-d-rch/                   # Reference implementation of the external research API
└── justfile             # Helpful automation commands (setup, tests, linting)
```

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for Python dependency management
- Docker (for containerised development, database, and Redis services)
- [just](https://github.com/casey/just) command runner

### 1. Bootstrap the project

Clone the repository and initialise the submodules. The project maintains both the vault and the research API implementation as Git submodules so workflows and integration tests can run without extra repositories.

```bash
git clone https://github.com/<your-org>/obs-graphs.git
cd obs-graphs
git submodule update --init --recursive
```

The `just setup` recipe installs Python dependencies with uv, ensures all submodules are up to date, and prepares a local `.env` file from `.env.example`.

```bash
just setup
```

### 2. Configure environment variables

All configuration is centralised in `.env`. Update it to reflect your environment. Important options include:

- `USE_*` toggles – enable or disable external integrations (LLM, Redis, research API mocks). By default `USE_MOCK_OLLAMA_DEEP_RESEARCHER=true`, but you can point to a live service by setting it to `false`.
- `USE_MOCK_OBS_GTWY` – when `true`, obs-graphs uses an in-process mock of the obs-gtwy gateway while the real API is not deployed.
- `OBS_GTWY_API_URL` / `OBS_GTWY_TIMEOUT_SECONDS` – connection details for the gateway responsible for materialising draft branches.
- `VAULT_SUBMODULE_PATH` – filesystem path to the local Obsidian vault submodule checkout.
- `OBS_GRAPHS_LLM_BACKEND` – default LLM backend (`ollama` or `mlx`) used by workflow nodes. Backend-specific options are defined in `src/obs_graphs/config/ollama_settings.py` and `src/obs_graphs/config/mlx_settings.py` (for example `OBS_GRAPHS_OLLAMA_MODEL`, `OLLAMA_HOST`, `OBS_GRAPHS_MLX_MODEL`, `OBS_GRAPHS_MLX_MAX_TOKENS`, etc.).
- `RESEARCH_API_URL` / related settings under `src/obs_graphs/config/research_api_settings.py` – connection details for the external deep-research API (served by the `olm-d-rch` submodule when mocks are disabled).

### 3. Run the application stack

Use Docker Compose via `just` recipes. The compose hierarchy works as follows:

- `docker-compose.yml` defines the core services (PostgreSQL, Redis, obs-api, celery-worker).
- `docker-compose.dev.override.yml` and `docker-compose.test.override.yml` add environment-specific tweaks.

Common commands:

```bash
just up          # Start development stack (obs-graphs + dependencies)
just down        # Stop development stack
just up-prod     # Start production-like stack
just down-prod   # Stop production-like stack
```

### 4. Execute tests

The `just` recipes wrap the supported test suites:

```bash
just unit-test         # Unit tests (host, fast)
just intg-test         # Integration tests (host, all dependencies mocked)
just sqlt-test         # SQLite-backed DB tests (host)
just docker-test       # Build production image, then run Postgres + e2e suite
just e2e-test          # Spin up stack and run pytest with PostgreSQL and mocked research service
```

E2E tests rely on PostgreSQL and will wait for `obs-api` to report healthy before executing tests.

### Selecting an LLM backend

Workflows obtain their language model through the dependency container. You can switch between Ollama and MLX without code changes:

- Set `OBS_GRAPHS_LLM_BACKEND=ollama` (default) to use an Ollama server. Configure the Ollama-specific settings in `src/obs_graphs/config/ollama_settings.py` (e.g. `OLLAMA_HOST`, `OBS_GRAPHS_OLLAMA_MODEL`).
- Set `OBS_GRAPHS_LLM_BACKEND=mlx` to use the MLX runtime on Apple Silicon. Configure MLX-specific settings in `src/obs_graphs/config/mlx_settings.py` (e.g. `OBS_GRAPHS_MLX_MODEL`, `OBS_GRAPHS_MLX_MAX_TOKENS`, `OBS_GRAPHS_MLX_TEMPERATURE`, `OBS_GRAPHS_MLX_TOP_P`). The runtime requires the `mlx-lm` package and an ARM64 Mac; the container raises a clear error on unsupported hardware.
- For development, enable `USE_MOCK_LLM=true` to wrap the existing mock responses behind the same protocol.

Individual workflow requests (API or Celery) can override the backend via the `backend` field; the choice is propagated to both the Article Proposal agent and the deep research client.

### 5. Quick API test

After starting the development stack with `just up`, verify the API is running:

```bash
# Check health endpoint
curl http://127.0.0.1:8001/health

# List available workflows
curl http://127.0.0.1:8001/api/v1/workflows
```

By default the research API client uses the in-repo mock. To exercise the real service, run the `olm-d-rch` submodule (or another compatible deployment), set `USE_MOCK_OLLAMA_DEEP_RESEARCHER=false`, and ensure the research API settings point to that endpoint.

## Workflow model

Workflows create a temporary directory, copy the contents of `submodules/obsidian-vault` into it, and then execute agents against that isolated copy. Agents interact with the local workspace through `VaultService`, which exposes helpers for summarising the vault and committing changes back via the GitHub API.

This design keeps runtime execution deterministic and avoids invoking Git operations inside the workflow beyond the initial submodule checkout.

## Contributing

1. Create feature branches from `main`.
2. Ensure `just format` and the test suite pass locally (`just docker-test`).
3. Keep the submodule changes focused on content updates—do not modify the submodule configuration directly in this repository.

## Troubleshooting

- **Submodule missing?** Re-run `git submodule update --init --recursive` to populate both `submodules/obsidian-vault` and `submodules/olm-d-rch`.
- **Using a different vault?** Update the `submodules/obsidian-vault` remote to point to your desired repository and adjust `VAULT_SUBMODULE_PATH` if you relocate the checkout.
- **Need to bypass external services?** Set the relevant `USE_MOCK_*` flags to `true`. Leave `USE_MOCK_OLLAMA_DEEP_RESEARCHER=true` for local mocks, or flip it to `false` and point the research client at a live `olm-d-rch` deployment.
