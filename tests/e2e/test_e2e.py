import httpx


class TestE2EAPI:
    """
    Class-based end-to-end tests for API endpoints.
    Tests run against the live containerized application stack.
    """

    def test_e2e_hello_world(self, api_base_url: str):
        """End-to-end smoke test for hello world endpoint."""
        with httpx.Client(base_url=api_base_url) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert response.json() == {"message": "Hello World"}

    def test_e2e_health_check(self, api_base_url: str):
        """End-to-end smoke test for health check endpoint."""
        with httpx.Client(base_url=api_base_url) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
