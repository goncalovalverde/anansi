"""Tests for the /api/insights endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.services import data_service


class TestInsightsEndpoint:
    """Tests for GET /api/insights/{dataset_id}."""

    def test_insights_dataset_not_found(self, client: TestClient):
        """GET /api/insights/nonexistent returns 404."""
        response = client.get("/api/insights/nonexistent-id")
        assert response.status_code == 404

    def test_insights_dataset_pending(self, client: TestClient, db_temp):
        """GET /api/insights/{dataset_id} with pending status returns 409."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        # Status is "pending" by default
        conn.close()

        response = client.get(f"/api/insights/{dataset_id}")
        assert response.status_code == 409

    def test_insights_dataset_loading(self, client: TestClient, db_temp):
        """GET /api/insights/{dataset_id} with loading status returns 409."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "loading")
        conn.close()

        response = client.get(f"/api/insights/{dataset_id}")
        assert response.status_code == 409

    def test_insights_dataset_failed(self, client: TestClient, db_temp):
        """GET /api/insights/{dataset_id} with failed status returns 409."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "failed", error="Load error")
        conn.close()

        response = client.get(f"/api/insights/{dataset_id}")
        assert response.status_code == 409

    def test_insights_dataset_ready(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/insights/{dataset_id} with ready status returns insights."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()

        mock_insights = [
            {"type": "ok", "message": "5 items completed this period"},
        ]
        with patch("backend.services.backlog_cache.get_insights_response", return_value=mock_insights):
            response = client.get(f"/api/insights/{dataset_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["type"] == "ok"

    def test_insights_returns_json(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/insights/{dataset_id} returns valid JSON."""
        from backend import database

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()

        mock_insights = [{"type": "warn", "message": "test"}]
        with patch("backend.services.backlog_cache.get_insights_response", return_value=mock_insights):
            response = client.get(f"/api/insights/{dataset_id}")

        assert response.status_code == 200
        assert isinstance(response.json(), list)
