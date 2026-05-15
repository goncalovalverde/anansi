"""Tests for the /api/charts endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.services import data_service


class TestChartsEndpoint:
    """Tests for GET /api/charts/{dataset_id}."""

    def test_charts_dataset_not_found(self, client: TestClient):
        """GET /api/charts/nonexistent returns 404."""
        response = client.get("/api/charts/nonexistent-id")
        assert response.status_code == 404
        assert "Dataset not found" in response.json()["detail"]

    def test_charts_dataset_pending(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} with pending status returns 409."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        # Status is "pending" by default
        conn.close()
        
        response = client.get(f"/api/charts/{dataset_id}")
        assert response.status_code == 409
        assert "not ready yet" in response.json()["detail"]

    def test_charts_dataset_loading(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} with loading status returns 409."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "loading")
        conn.close()
        
        response = client.get(f"/api/charts/{dataset_id}")
        assert response.status_code == 409
        assert "not ready yet" in response.json()["detail"]

    def test_charts_dataset_failed(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} with failed status returns 422."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "failed", error="Load error")
        conn.close()
        
        response = client.get(f"/api/charts/{dataset_id}")
        assert response.status_code == 422
        assert "loading failed" in response.json()["detail"]

    def test_charts_dataset_ready(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/charts/{dataset_id} with ready status returns charts."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()
        
        with patch("backend.services.backlog_cache.get_dashboard_response") as mock_charts:
            mock_charts.return_value = {
                "charts": [
                    {"name": "test_chart", "data": [1, 2, 3]}
                ]
            }
            response = client.get(f"/api/charts/{dataset_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "charts" in data

    def test_charts_rendering_error(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} returns 500 if rendering fails."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        conn.close()
        
        with patch("backend.services.backlog_cache.get_dashboard_response") as mock_charts:
            mock_charts.side_effect = ValueError("Rendering failed")
            response = client.get(f"/api/charts/{dataset_id}")
        
        assert response.status_code == 500
        assert "rendering failed" in response.json()["detail"]
