"""E2E test specific fixtures.

Common fixtures like vault_fixture, db_session, etc. are in tests/conftest.py.
This file contains only E2E-specific fixtures like e2e_setup and api_base_url.
"""

import os
import subprocess
import time
from typing import Generator, List
from unittest.mock import Mock, patch

import httpx
import pytest

from src.container import DependencyContainer


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Return the base URL for the API service under test."""
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    return f"http://{host_bind_ip}:{host_port}"


def _wait_for_health_check(url: str, timeout: int = 120, interval: int = 5) -> None:
    """Poll the service health endpoint until it responds with HTTP 200."""

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ Service at {url} is healthy")
                return
            print(
                f"⚠️ Health check at {url} returned {response.status_code}; retrying in {interval}s..."
            )
        except httpx.RequestError as exc:
            print(
                f"⏳ Waiting for service at {url} (error: {exc}); retrying in {interval}s..."
            )

        time.sleep(interval)

    raise TimeoutError(
        f"Service at {url} did not become ready within {timeout} seconds"
    )


def _wait_for_research_service_ready(
    docker_command: List[str], compose_common_args: List[str], timeout: int = 120
) -> None:
    """Wait for the research-api container to report a healthy status."""

    start_time = time.time()
    check_interval = 5

    while time.time() - start_time < timeout:
        try:
            ps_command = (
                docker_command + compose_common_args + ["ps", "--format", "json"]
            )
            result = subprocess.run(
                ps_command, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                import json

                services = [
                    json.loads(line) for line in result.stdout.splitlines() if line
                ]
                for service in services:
                    if "research-api" in service.get("Service", ""):
                        health = service.get("Health", "")
                        if health == "healthy":
                            print("✅ Service 'research-api' is healthy")
                            return
                        print(
                            f"⏳ Waiting for service 'research-api' to become healthy (current: {health or 'starting'})..."
                        )

            time.sleep(check_interval)
        except Exception as exc:  # pragma: no cover - diagnostic logging only
            print(f"⚠️ Error while checking service 'research-api': {exc}")
            time.sleep(check_interval)

    raise TimeoutError(
        "Service 'research-api' did not become healthy within the expected timeout"
    )


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """Manage Docker Compose lifecycle for E2E tests with automatic health checks."""

    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    project_name = os.getenv("PROJECT_NAME", "obs-graph")
    test_project_name = f"{project_name}-test"
    use_mock_research = os.getenv("USE_MOCK_RESEARCH_API", "true").lower() == "true"

    compose_common_args = [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.research.override.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
    ]

    compose_up_command = docker_command + compose_common_args + ["up", "-d", "--build"]
    compose_down_command = (
        docker_command + compose_common_args + ["down", "-v", "--remove-orphans"]
    )

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    api_health_url = f"http://{host_bind_ip}:{host_port}/health"

    try:
        print("\n🚀 Starting E2E test services with docker compose...")
        subprocess.run(compose_up_command, check=True, timeout=300)

        print("⏳ Waiting for service 'obs-api' to become healthy...")
        _wait_for_health_check(api_health_url)

        if not use_mock_research:
            print("⏳ Waiting for service 'research-api' to become healthy...")
            _wait_for_research_service_ready(docker_command, compose_common_args)

        print("✅ All services are ready")
        yield
    except (subprocess.CalledProcessError, TimeoutError) as exc:
        print(f"\n🛑 E2E setup failed: {exc}")
        subprocess.run(compose_down_command, check=False)
        pytest.fail(f"E2E setup failed: {exc}")
    finally:
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=False)


@pytest.fixture(autouse=True)
def mock_github_client_for_e2e():
    """Mock GitHub client for e2e tests to avoid real API calls."""
    mock_client = Mock()
    mock_client.clone_repository.return_value = None
    mock_client.create_branch.return_value = None
    mock_client.commit_and_push.return_value = True

    mock_pr = Mock()
    mock_pr.html_url = "https://github.com/test/repo/pull/1"
    mock_client.create_pull_request.return_value = mock_pr

    with patch.object(
        DependencyContainer, "get_github_client", return_value=mock_client
    ):
        yield


@pytest.fixture(autouse=True)
def mock_graph_builder_run_workflow():
    """Mock GraphBuilder.run_workflow for e2e tests to avoid real workflow execution."""
    from src.api.v1.graph import GraphBuilder, WorkflowResult

    mock_result = WorkflowResult(
        success=True,
        changes=[],
        summary="Mock workflow completed successfully",
        node_results={},
        pr_url="https://github.com/test/repo/pull/1",
        branch_name="mock-branch",
    )
    with patch.object(GraphBuilder, "run_workflow", return_value=mock_result):
        yield
