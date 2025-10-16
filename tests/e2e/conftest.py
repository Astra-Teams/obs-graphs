"""E2E test specific fixtures.

Common fixtures like vault_fixture, db_session, etc. are in tests/conftest.py.
This file contains only E2E-specific fixtures like e2e_setup and api_base_url.
"""

import os
import subprocess
import time
from typing import Generator
from unittest.mock import AsyncMock

import httpx
import pytest

from src.obs_glx.protocols import StlConnClientProtocol


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Return the base URL for the API service under test."""
    host_bind_ip = os.getenv("OBS_GLX_HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("OBS_GLX_TEST_PORT", "8002")
    return f"http://{host_bind_ip}:{host_port}"


@pytest.fixture(scope="session")
def mock_llm_client() -> AsyncMock:
    """Create a mock LLM client for E2E tests."""
    client = AsyncMock(spec=StlConnClientProtocol)

    # Mock response for research_topic_proposal
    mock_response = AsyncMock()
    mock_response.content = "Test Research Topic"
    client.invoke.return_value = mock_response

    return client


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


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """Manage Docker Compose lifecycle for E2E tests with automatic health checks."""

    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    project_name = os.getenv("OBS_GLX_PROJECT_NAME", "obs-glx")
    test_project_name = f"{project_name}-test"

    compose_common_args = [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
    ]

    compose_up_command = docker_command + compose_common_args + ["up", "-d", "--build"]
    compose_down_command = (
        docker_command + compose_common_args + ["down", "-v", "--remove-orphans"]
    )

    # Prepare environment variables for subprocess
    env = os.environ.copy()
    env["OBS_GLX_USE_SQLITE"] = "false"
    env["OBS_GLX_USE_MOCK_STL_CONN"] = (
        "true"  # E2E uses mock stl-conn (requires separate LLM server)
    )
    env["OBS_GLX_USE_MOCK_REDIS"] = "false"  # E2E uses real Redis
    env["OBS_GLX_USE_MOCK_STARPROBE"] = "true"
    env["OBS_GLX_USE_MOCK_GITHUB"] = "true"

    host_bind_ip = os.getenv("OBS_GLX_HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("OBS_GLX_TEST_PORT", "8002")
    api_health_url = f"http://{host_bind_ip}:{host_port}/health"

    try:
        print("\n🚀 Starting E2E test services with docker compose...")
        subprocess.run(compose_up_command, check=True, timeout=300, env=env)

        print("⏳ Waiting for service 'obs-glx-api' to become healthy...")
        _wait_for_health_check(api_health_url)

        print("✅ All services are ready")
        yield
    except (subprocess.CalledProcessError, TimeoutError) as exc:
        print(f"\n🛑 E2E setup failed: {exc}")
        subprocess.run(compose_down_command, check=False, env=env)
        pytest.fail(f"E2E setup failed: {exc}")
    finally:
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=False, env=env)
