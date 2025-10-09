# Obsidian Graphs

Obsidian Graphs is an AI-powered workflow automation service for Obsidian vaults. It orchestrates modular LangGraph agents that can analyse, organise, and enhance a knowledge base by proposing and applying changes through GitHub pull requests.

## What's in the box?

- **FastAPI** application that exposes workflow orchestration endpoints.
- **LangGraph** powered agents for article improvements, classification, cross-referencing, and vault quality audits.
- **Pydantic `BaseSettings` configuration** with dedicated modules for database, Redis, and research API settings.
- **Git submodules** for external integrations, including the shared Obsidian vault checkout.

## Repository layout

```
├── src/                 # Application code, services, agents, configuration
├── tests/               # Unit, database, and end-to-end tests
├── dev/mock_vault/      # Fixtures used when mock services are enabled
├── submodules/
│   ├── obsidian-vault/  # Local checkout of the vault used during workflows
│   └── ollama-deep-researcher/  # Reference implementation of the external research API
└── justfile             # Helpful automation commands (setup, tests, linting)
```

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) for Python dependency management
- Docker (for containerised development, database, and Redis services)

### 1. Bootstrap the project

Clone the repository and initialise the submodules. The project maintains a shared Obsidian vault as a Git submodule so workflows can operate on a local copy of the content without cloning at runtime.

```bash
git clone https://github.com/<your-org>/obs-graphs.git
cd obs-graphs
git submodule update --init --recursive
```

The `just setup` recipe installs Python dependencies with uv, ensures all submodules are up to date (including `submodules/obsidian-vault`), and prepares a local `.env` file from `.env.example`.

```bash
uv tool install just     # if you do not already have just installed
just setup
```

### 2. Configure environment variables

All configuration is centralised in `src/config/obs_graphs_settings.py` using `pydantic-settings`. Update `.env` to reflect your environment. Important options include:

- `USE_*` toggles – enable or disable external integrations (GitHub, LLM, Redis, Research API).
- `VAULT_SUBMODULE_PATH` – filesystem path to the local Obsidian vault submodule checkout. The workflow runner copies this directory into a temporary workspace for every run.
- `OBSIDIAN_VAULT_GITHUB_TOKEN` / `OBSIDIAN_VAULT_REPOSITORY` – credentials for committing changes back to GitHub.

### 3. Run the application stack

Use Docker Compose via `just up` to start the API, Redis, and supporting services defined in `docker-compose.yml` and `docker-compose.dev.override.yml`.

```bash
just up
```

Bring the services down with:

```bash
just down
```

### 4. Execute tests

The `just` recipes wrap the supported test suites:

```bash
just unit-test         # Run unit tests with uv/pytest
just sqlt-test         # Execute SQLite-backed DB tests without Docker
just docker-test       # Build the production image and run Postgres + e2e tests
```

## Workflow model

Workflows create a temporary directory, copy the contents of `submodules/obsidian-vault` into it, and then execute agents against that isolated copy. Agents interact with the local workspace through `VaultService`, which exposes helpers for summarising the vault and committing changes back via the GitHub API.

This design keeps runtime execution deterministic and avoids invoking Git operations inside the workflow beyond the initial submodule checkout.

## Contributing

1. Create feature branches from `main`.
2. Ensure `just format` and the test suite pass locally.
3. Keep the vault submodule changes focused on content updates—do not modify the submodule configuration directly in this repository.

## Troubleshooting

- **Submodule missing?** Re-run `git submodule update --init --recursive` to populate both `submodules/obsidian-vault` and `submodules/ollama-deep-researcher`.
- **Using a different vault?** Update the `submodules/obsidian-vault` remote to point to your desired repository and adjust `VAULT_SUBMODULE_PATH` if you relocate the checkout.
- **Need to bypass external services?** Set the relevant `USE_MOCK_*` flags to `true` and provide fixtures under `dev/mock_vault/`.
