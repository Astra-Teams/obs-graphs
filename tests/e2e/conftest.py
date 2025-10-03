import os
import subprocess
import time
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set environment variables for Docker Compose
os.environ["HOST_BIND_IP"] = os.getenv("HOST_BIND_IP", "127.0.0.1")
os.environ["TEST_PORT"] = os.getenv("TEST_PORT", "8002")


@pytest.fixture(scope="session")
def api_base_url():
    """
    Provides the base URL for the API service.
    Uses the e2e_setup fixture for container management.
    """
    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    return f"http://{host_bind_ip}:{host_port}"


def _is_service_ready(url: str, expected_status: int = 200) -> bool:
    """Check if HTTP service is ready by making a request."""
    try:
        response = httpx.get(url, timeout=5)
        if response.status_code == expected_status:
            return True
    except httpx.RequestError:
        return False
    return False


def _wait_for_service(url: str, timeout: int = 120, interval: int = 5) -> None:
    """Wait for HTTP service to be ready with timeout."""
    print(f"Waiting for service to be ready at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if _is_service_ready(url):
            print(f"✅ Service at {url} is ready!")
            return
        print(f"⏳ Service not yet ready, retrying in {interval}s...")
        time.sleep(interval)
    raise TimeoutError(
        f"Service at {url} did not become ready within {timeout} seconds"
    )


@pytest.fixture(scope="session", autouse=True)
def e2e_setup() -> Generator[None, None, None]:
    """
    Manages the lifecycle of the application for end-to-end testing.
    This fixture assumes 'make e2e-test' will manage the containers,
    but it performs the health check wait just in case.
    """
    use_sudo = os.getenv("SUDO") == "true"
    docker_command = ["sudo", "docker"] if use_sudo else ["docker"]

    host_bind_ip = os.getenv("HOST_BIND_IP", "127.0.0.1")
    host_port = os.getenv("TEST_PORT", "8002")
    health_url = f"http://{host_bind_ip}:{host_port}/health"

    project_name = os.getenv("PROJECT_NAME", "fastapi-template")
    test_project_name = f"{project_name}-test"

    # Define compose commands
    compose_up_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
        "up",
        "-d",
        "--build",  # e2e-test always performs build
    ]
    compose_down_command = docker_command + [
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.override.yml",
        "--project-name",
        test_project_name,
        "down",
        "--remove-orphans",
    ]

    try:
        print("\n🚀 Starting E2E test services with docker-compose...")
        # Start containers (mimics/ensures startup by make e2e-test)
        subprocess.run(compose_up_command, check=True, timeout=300)

        _wait_for_service(health_url, timeout=120, interval=5)

        yield

    except (subprocess.CalledProcessError, TimeoutError) as e:
        print(f"\n🛑 E2E setup failed: {e}")
        subprocess.run(compose_down_command, check=False)  # Attempt cleanup
        pytest.fail(f"E2E setup failed: {e}")

    finally:
        # Stop services
        print("\n🛑 Stopping E2E services...")
        subprocess.run(compose_down_command, check=False)
