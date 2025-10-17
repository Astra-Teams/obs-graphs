# Obsidian Galaxy

Obsidian Galaxy is an AI-powered workflow automation service for Obsidian vaults. It orchestrates modular LangGraph agents that can analyse, organise, and enhance a knowledge base by proposing and applying changes through GitHub-managed draft branches.

## What's in the box?

- **FastAPI** application that exposes workflow orchestration endpoints.
- **LangGraph** powered agents for article improvements, classification, cross-referencing, and vault quality audits.
- **Pydantic `BaseSettings` configuration** with dedicated modules for database, Redis, and research API settings.
- **Pluggable LLM backends** via the nexus SDK, providing a unified interface to various LLM providers.
- **Git submodules** for external integrations, including the shared Obsidian vault checkout and the reference deep-research API.
- **First-party integrations** for publishing drafts directly to GitHub (`obs_glx.services.github_draft_service`) and deep research through the shared `starprobe_sdk`, plus a first-party `obs_graphs_sdk` for workflow execution.

## Directory Structure

```
├── src/obs_glx/       # Main application package
│   ├── api/             # FastAPI endpoints and schemas
│   ├── celery/          # Celery tasks for async workflow execution
│   ├── clients/         # External service clients (LLM adapters)
│   ├── config/          # Configuration modules
│   ├── dependencies.py  # FastAPI-native dependency injection hub
│   ├── db/              # Database models and session management
│   ├── graphs/          # LangGraph workflow definitions
│   │   ├── factory.py          # Factory function for workflow graph builders
│   │   ├── protocol.py         # WorkflowGraphProtocol interface
│   │   └── article_proposal/   # Article proposal workflow
│   ├── protocols/       # Protocol definitions for dependency injection
│   ├── services/        # Business logic services
│   └── main.py          # FastAPI application entry point
├── tests/               # Unit, database, and end-to-end tests
├── dev/                 # Development fixtures and mocks
├── submodules/          # Git submodules for external dependencies
│   ├── constellations/              # Local checkout of the vault used during workflows
│   └── starprobe/                   # Reference implementation of the external research API
├── sdk/                 # First-party Python SDK mirroring the starprobe layout
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

- `USE_*` toggles – enable or disable external integrations (LLM, Redis, research API mocks). By default `USE_MOCK_STARPROBE=true`, but you can point to a live service by setting it to `false`.
- `OBS_GLX_USE_MOCK_GITHUB` – when `true`, obs-glx uses an in-process mock of the GitHub draft service while credentials are not configured.
- `OBS_GLX_GITHUB_REPO` – repository (`owner/repo`) where draft branches should be published.
- `OBS_GLX_GITHUB_TOKEN` – Personal Access Token with rights to create branches and upload files.

- `NEXUS_BASE_URL` – base URL for the nexus service providing LLM access.
- `NEXUS_DEFAULT_BACKEND` – default backend (`ollama` or `mlx`) targeted by the nexus SDK clients.
- `USE_MOCK_NEXUS` – when `true`, uses mock LLM responses for development and testing.

### 3. Run the application stack

Use Docker Compose via `just` recipes. The compose hierarchy works as follows:

- `docker-compose.yml` defines the core services (PostgreSQL, Redis, obs-api, worker).
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
just sdk-test          # SDK-specific tests (host, fast)
just intg-test         # Integration tests (host, all dependencies mocked)
just sqlt-test         # SQLite-backed DB tests (host)
just docker-test       # Build production image, then run Postgres + e2e suite
just e2e-test          # Spin up stack and run pytest with PostgreSQL and mocked research service
```

E2E tests rely on PostgreSQL and will wait for `obs-api` to report healthy before executing tests.

### LLM Integration

Workflows obtain their language model through the nexus SDK, which provides a unified interface to various LLM providers. Configuration is managed via environment variables:

- Set `NEXUS_BASE_URL` to the URL of your nexus service instance.
- Choose the default runtime by setting `NEXUS_DEFAULT_BACKEND` (`ollama` or `mlx`).
- For development, enable `USE_MOCK_NEXUS=true` to use mock LLM responses instead of calling the real service.

The nexus service abstracts away the complexities of different LLM backends, allowing workflows to focus on their logic without backend-specific code.

### 5. Quick API test

After starting the development stack with `just up`, verify the API is running:

```bash
# Check health endpoint
curl http://127.0.0.1:8001/health

# Check API status
curl http://127.0.0.1:8001/api/workflows/status
```

By default the research API client uses the in-repo mock. To exercise the real service, run the `starprobe` submodule (or another compatible deployment), set `USE_MOCK_STARPROBE=false`, and ensure the research API settings point to that endpoint.

### Workflow run payload

To launch a workflow, submit a `POST /api/workflows/{workflow_type}/run` request with an ordered list of prompts. The first entry is treated as the primary instruction, while subsequent entries represent follow-up steps the agents should consider. Each prompt is trimmed server-side and must contain non-whitespace content.

Currently supported workflow types:
- `article-proposal`: Research topic proposal and article creation

```bash
curl -X POST http://127.0.0.1:8001/api/workflows/article-proposal/run \
  -H "Content-Type: application/json" \
  -d '{
        "prompts": [
          "Generate research topic ideas for retrieval-augmented generation",
          "Select the most actionable topic",
          "Draft a 2 paragraph article outline"
        ],
        "async_execution": true
      }'
```

Validation rules:

- The `prompts` array must contain at least one item.
- Every entry is normalised with `str.strip()` and must remain non-empty after trimming.
- Optional fields such as `strategy` continue to work as before.

### Workflow status polling

Clients can poll `GET /api/workflows/{workflow_id}` to observe detailed progress for
long-running executions. In addition to the status flags, the response now
includes:

- `progress_message`: a human-readable description of the current stage (for example,
  `Running Deep Research (2/3)` or `Workflow completed successfully`).
- `progress_percent`: an integer between 0 and 100 that estimates overall completion.

The progress metadata is updated throughout the workflow lifecycle, including
updates from each LangGraph node as it begins and finishes. This allows mobile
and web clients to present meaningful status updates instead of a long-lived
`RUNNING` indicator.

## SDK

This repository includes a Python SDK that mirrors the `starprobe` SDK layout and exposes the workflow run endpoint.

### Usage

```python
from obs_glx_sdk import WorkflowApiClient, WorkflowRequest

client = WorkflowApiClient(base_url="http://localhost:8001")
payload = WorkflowRequest(
  prompts=[
    "Generate research topic ideas for retrieval-augmented generation",
    "Select the most actionable topic",
    "Draft a 2 paragraph article outline",
  ],
  async_execution=True,
)

response = client.run_workflow("article-proposal", payload)

if response.status == "COMPLETED":
  print("Workflow executed successfully")
else:
  print(response.message)
```

For tests, `obs_glx_sdk.MockWorkflowApiClient` records invocations and returns deterministic responses without performing network IO.

## Workflow model

Workflows create a temporary directory, copy the contents of `submodules/constellations` into it, and then execute agents against that isolated copy. Agents interact with the local workspace through `VaultService`, which exposes helpers for summarising the vault and committing changes back via the GitHub API.

This design keeps runtime execution deterministic and avoids invoking Git operations inside the workflow beyond the initial submodule checkout.

## Contributing

1. Create feature branches from `main`.
2. Ensure `just format` and the test suite pass locally (`just docker-test`).
3. Keep the submodule changes focused on content updates—do not modify the submodule configuration directly in this repository.

## Troubleshooting

- **Submodule missing?** Re-run `git submodule update --init --recursive` to populate both `submodules/constellations` and `submodules/starprobe`.
- **Using a different vault?** Update the `submodules/constellations` remote to point to your desired repository.
- **Need to bypass external services?** Set the relevant `USE_MOCK_*` flags to `true`. Leave `USE_MOCK_STARPROBE=true` for local mocks, or flip it to `false` and point the research client at a live `starprobe` deployment.
