"""Tests for the /api/flow endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.services import data_service


class TestFlowEndpoint:
    """Tests for GET /api/flow/{dataset_id}."""

    def test_flow_dataset_not_found(self, client: TestClient):
        """GET /api/flow/nonexistent returns 404."""
        response = client.get("/api/flow/nonexistent-id")
        assert response.status_code == 404

    def test_flow_dataset_pending(self, client: TestClient, db_temp):
        """GET /api/flow/{dataset_id} with pending status returns 409."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        # Status is "pending" by default
        conn.close()

        response = client.get(f"/api/flow/{dataset_id}")
        assert response.status_code == 409
        assert "not ready yet" in response.json()["detail"]

    def test_flow_dataset_loading(self, client: TestClient, db_temp):
        """GET /api/flow/{dataset_id} with loading status returns 409."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "loading")
        conn.close()

        response = client.get(f"/api/flow/{dataset_id}")
        assert response.status_code == 409
        assert "not ready yet" in response.json()["detail"]

    def test_flow_dataset_failed(self, client: TestClient, db_temp):
        """GET /api/flow/{dataset_id} with failed status returns 422."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "failed", error="Load error")
        conn.close()

        response = client.get(f"/api/flow/{dataset_id}")
        assert response.status_code == 422
        assert "loading failed" in response.json()["detail"]

    def test_flow_dataset_ready(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/flow/{dataset_id} with ready status returns flow data."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()

        with patch("backend.services.backlog_cache.get_flow_response") as mock_flow:
            mock_flow.return_value = {
                "flow": {"type": "scatter", "data": []}
            }
            response = client.get(f"/api/flow/{dataset_id}")

        assert response.status_code == 200
        data = response.json()
        assert "flow" in data

    def test_flow_rendering_error(self, client: TestClient, db_temp):
        """GET /api/flow/{dataset_id} returns 500 if rendering fails."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        conn.close()

        with patch("backend.services.backlog_cache.get_flow_response") as mock_flow:
            mock_flow.side_effect = ValueError("Flow rendering failed")
            response = client.get(f"/api/flow/{dataset_id}")

        assert response.status_code == 500
        assert "rendering failed" in response.json()["detail"]

    def test_flow_returns_json(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/flow/{dataset_id} returns valid JSON response."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()

        with patch("backend.services.backlog_cache.get_flow_response") as mock_flow:
            mock_flow.return_value = {"cumulative_flow": {}}
            response = client.get(f"/api/flow/{dataset_id}")

        assert response.status_code == 200
        assert isinstance(response.json(), dict)
