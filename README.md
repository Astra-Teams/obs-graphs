# Obsidian Graphs

Obsidian Graphs is an AI-powered workflow automation service for Obsidian vaults. It orchestrates modular LangGraph agents that can analyse, organise, and enhance a knowledge base by proposing and applying changes through GitHub pull requests.

## What's in the box?

- **FastAPI** application that exposes workflow orchestration endpoints.
- **LangGraph** powered agents for article improvements, classification, cross-referencing, and vault quality audits.
- **Pydantic `BaseSettings` configuration** with dedicated modules for database, Redis, and research API settings.
- **Git submodules** for external integrations, including the shared Obsidian vault checkout and the reference deep-research API.

## Repository layout

```
├── src/                 # Application code, services, agents, configuration
├── tests/               # Unit, database, and end-to-end tests
├── dev/mock_vault/      # Fixtures used when mock services are enabled
├── submodules/
│   ├── obsidian-vault/              # Local checkout of the vault used during workflows
│   └── ollama-deep-researcher/      # Reference implementation of the external research API
├── docker-compose.research.override.yml  # Shared overlay that adds research-api to the stack
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

- `USE_*` toggles – enable or disable external integrations (GitHub, LLM, Redis, Research API).
- `RESEARCH_API_URL` / `RESEARCH_API_OLLAMA_MODEL` – defaults to the in-network research container; point these at an external service for production-like deployments.
- `OBSIDIAN_VAULT_GITHUB_TOKEN` / `OBSIDIAN_VAULT_REPOSITORY` – credentials for committing changes back to GitHub.
- `VAULT_SUBMODULE_PATH` – filesystem path to the local Obsidian vault submodule checkout.

### 3. Run the application stack

Use Docker Compose via `just` recipes. The compose hierarchy works as follows:

- `docker-compose.yml` defines the core services (PostgreSQL, Redis, obs-api, celery-worker).
- `docker-compose.research.override.yml` adds the `research-api` container and marks it healthy before other services start.
- `docker-compose.dev.override.yml` and `docker-compose.test.override.yml` add environment-specific tweaks.

Common commands:

```bash
just up          # Start development stack (obs-graphs + research-api + dependencies)
just down        # Stop development stack
just up-prod     # Start production-like stack (obs-graphs only; expects external research API)
just down-prod   # Stop production-like stack
```

### 4. Execute tests

The `just` recipes wrap the supported test suites:

```bash
just unit-test         # Unit tests (host, fast)
just sqlt-test         # SQLite-backed DB tests (host)
just docker-test       # Build production image, then run Postgres + mock e2e suite inside containers
just e2e-test-mock     # Spin up stack and run pytest inside obs-api with mocked research service
just e2e-test-real     # Spin up stack and run pytest inside obs-api against the real research service
```

Both E2E recipes rely on PostgreSQL and will wait for `obs-api` (and `research-api` when applicable) to report healthy before executing tests.

## Workflow model

Workflows create a temporary directory, copy the contents of `submodules/obsidian-vault` into it, and then execute agents against that isolated copy. Agents interact with the local workspace through `VaultService`, which exposes helpers for summarising the vault and committing changes back via the GitHub API.

This design keeps runtime execution deterministic and avoids invoking Git operations inside the workflow beyond the initial submodule checkout.

## Contributing

1. Create feature branches from `main`.
2. Ensure `just format` and the test suite pass locally (`just docker-test`, `just e2e-test-real` when applicable).
3. Keep the submodule changes focused on content updates—do not modify the submodule configuration directly in this repository.

## Troubleshooting

- **Submodule missing?** Re-run `git submodule update --init --recursive` to populate both `submodules/obsidian-vault` and `submodules/ollama-deep-researcher`.
- **Using a different vault?** Update the `submodules/obsidian-vault` remote to point to your desired repository and adjust `VAULT_SUBMODULE_PATH` if you relocate the checkout.
- **Need to bypass external services?** Set the relevant `USE_MOCK_*` flags to `true`. For integration tests, `just e2e-test-mock` keeps PostgreSQL but stubs research responses.
