"""Tests for the /api/trends endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.services import data_service


class TestTrendsEndpoint:
    """Tests for GET /api/trends/{dataset_id}."""

    def test_trends_dataset_not_found(self, client: TestClient):
        """GET /api/trends/nonexistent returns 404."""
        response = client.get("/api/trends/nonexistent-id")
        assert response.status_code == 404

    def test_trends_dataset_pending(self, client: TestClient, db_temp):
        """GET /api/trends/{dataset_id} with pending status returns 409."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        # Status is "pending" by default
        conn.close()
        
        response = client.get(f"/api/trends/{dataset_id}")
        assert response.status_code == 409
        assert "not ready" in response.json()["detail"]

    def test_trends_dataset_loading(self, client: TestClient, db_temp):
        """GET /api/trends/{dataset_id} with loading status returns 409."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "loading")
        conn.close()
        
        response = client.get(f"/api/trends/{dataset_id}")
        assert response.status_code == 409
        assert "not ready" in response.json()["detail"]

    def test_trends_dataset_failed(self, client: TestClient, db_temp):
        """GET /api/trends/{dataset_id} with failed status returns 409."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "failed", error="Load error")
        conn.close()
        
        response = client.get(f"/api/trends/{dataset_id}")
        assert response.status_code == 409

    def test_trends_dataset_ready(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/trends/{dataset_id} with ready status returns trend data."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()
        
        mock_response = {
            "cumulative_flow": {"layout": {}},
            "monthly_throughput": {"layout": {}},
            "epic_progress": {"layout": {}},
        }
        with patch("backend.services.backlog_cache.get_trends_response", return_value=mock_response):
            response = client.get(f"/api/trends/{dataset_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "cumulative_flow" in data
        assert "monthly_throughput" in data
        assert "epic_progress" in data

    def test_trends_response_structure(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/trends/{dataset_id} returns all required trend charts."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()
        
        mock_response = {
            "cumulative_flow": {"type": "scatter", "data": []},
            "monthly_throughput": {"type": "scatter", "data": []},
            "epic_progress": {"type": "scatter", "data": []},
        }
        with patch("backend.services.backlog_cache.get_trends_response", return_value=mock_response):
            response = client.get(f"/api/trends/{dataset_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all trend types are present
        required_trends = ["cumulative_flow", "monthly_throughput", "epic_progress"]
        for trend in required_trends:
            assert trend in data
            assert isinstance(data[trend], dict)

    def test_trends_partial_failure_with_graceful_fallback(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/trends/{dataset_id} handles failures gracefully."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()
        
        with patch("backend.services.backlog_cache.get_trends_response", side_effect=Exception("Render failed")):
            response = client.get(f"/api/trends/{dataset_id}")
        
        # Should return 500 since we now let exceptions bubble to error handler
        assert response.status_code == 500

    def test_trends_returns_valid_json(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/trends/{dataset_id} returns valid JSON structure."""
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()
        
        mock_response = {
            "cumulative_flow": {"type": "scatter", "data": []},
            "monthly_throughput": {"type": "bar", "data": []},
            "epic_progress": {"type": "scatter", "data": []},
        }
        with patch("backend.services.backlog_cache.get_trends_response", return_value=mock_response):
            response = client.get(f"/api/trends/{dataset_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        for key, value in data.items():
            assert isinstance(value, dict), f"Trend {key} should be a dict"
