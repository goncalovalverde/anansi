"""Tests for the /api/health endpoint."""

from fastapi.testclient import TestClient


class TestHealth:
    """Tests for the health check endpoint."""

    def test_health_check_without_slash(self, client: TestClient):
        """GET /api/health returns 200 with ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_check_with_slash(self, client: TestClient):
        """GET /api/health/ (with trailing slash) also returns 200."""
        response = client.get("/api/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_check_content_type(self, client: TestClient):
        """Health check response has application/json content type."""
        response = client.get("/api/health")
        assert response.headers["content-type"] == "application/json"

    def test_health_check_response_body_structure(self, client: TestClient):
        """Health check response contains status key with 'ok' value."""
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
