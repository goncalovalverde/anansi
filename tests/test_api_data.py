"""Tests for the /api/data endpoints."""

import pytest
import uuid
import json
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.services import data_service


class TestDataLoad:
    """Tests for POST /api/data/load."""

    def test_load_data_returns_dataset_id(self, client: TestClient, db_temp):
        """POST /api/data/load returns dataset_id and cached=false."""
        # Set minimal required config with auth
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "basic",
                "jira_username": "testuser",
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )
        
        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config"):
                response = client.post("/api/data/load")
        
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert isinstance(data["dataset_id"], str)
        assert len(data["dataset_id"]) > 0  # Should be a valid UUID
        assert data["cached"] is False

    def test_load_data_missing_jira_url(self, client: TestClient):
        """POST /api/data/load returns 400 if jira_url is missing."""
        client.put(
            "/api/config",
            json={
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "basic",
                "jira_username": "testuser",
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )
        
        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config") as mock_validate:
                mock_validate.side_effect = ValueError("URL is required")
                response = client.post("/api/data/load")
        
        assert response.status_code == 400

    def test_load_data_missing_jql_query(self, client: TestClient):
        """POST /api/data/load returns 400 if JQL query is empty."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "",
                "jira_auth_method": "basic",
                "jira_username": "testuser",
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )
        
        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config"):
                response = client.post("/api/data/load")
        
        assert response.status_code == 400

    def test_load_data_caching_same_config(self, client: TestClient, db_temp):
        """POST /api/data/load returns cached=true for same config."""
        # Set config with auth
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "basic",
                "jira_username": "testuser",
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )
        
        # First load
        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config"):
                response1 = client.post("/api/data/load")
        assert response1.status_code == 200
        dataset_id_1 = response1.json()["dataset_id"]
        assert response1.json()["cached"] is False
        
        # Mark dataset as ready to enable caching
        import sqlite3
        from backend import database
        conn = database.get_db(db_temp)
        conn.execute(
            "UPDATE datasets SET status='ready' WHERE id=?",
            (dataset_id_1,)
        )
        conn.commit()
        conn.close()
        
        # Second load with same config should return cached
        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config"):
                response2 = client.post("/api/data/load")
        assert response2.status_code == 200
        assert response2.json()["cached"] is True
        assert response2.json()["dataset_id"] == dataset_id_1

    def test_load_data_csv_mode_requires_file(self, client: TestClient):
        """POST /api/data/load returns 400 if CSV mode without file path."""
        client.put(
            "/api/config",
            json={
                "input_mode": "csv",
                "input_csv_file": "",
            }
        )
        
        with patch("backend.services.data_service.load_data_task"):
            response = client.post("/api/data/load")
        
        assert response.status_code == 400


class TestDataStatus:
    """Tests for GET /api/data/{dataset_id}/status."""

    def test_get_status_pending(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status returns pending status."""
        import sqlite3
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        conn.close()
        
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["error"] is None
        assert data["progress_loaded"] == 0
        assert data["progress_total"] == 0

    def test_get_status_loading(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status returns loading status with progress."""
        import sqlite3
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "loading")
        data_service.update_dataset_progress(conn, dataset_id, 50, 100)
        conn.close()
        
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "loading"
        assert data["progress_loaded"] == 50
        assert data["progress_total"] == 100

    def test_get_status_ready(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status returns ready status."""
        import sqlite3
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        conn.close()
        
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["error"] is None

    def test_get_status_failed(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status returns failed status with error."""
        import sqlite3
        from backend import database
        
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        error_msg = "Connection timeout"
        data_service.update_dataset_status(conn, dataset_id, "failed", error=error_msg)
        conn.close()
        
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == error_msg

    def test_get_status_nonexistent(self, client: TestClient):
        """GET /api/data/nonexistent/status returns 404."""
        response = client.get(f"/api/data/invalid-uuid/status")
        assert response.status_code == 404
        assert "Dataset not found" in response.json()["detail"]


class TestDataUploadCSV:
    """Tests for POST /api/data/upload-csv."""

    def test_upload_csv_valid_file(self, client: TestClient):
        """POST /api/data/upload-csv accepts valid CSV file."""
        # Create a valid CSV
        csv_content = b"""Key,Summary,Created,Status
TEST-1,First Issue,2024-01-01,Done
TEST-2,Second Issue,2024-01-02,In Progress"""
        
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        with patch("backend.reader.csv.read_from_string") as mock_read:
            mock_read.return_value = MagicMock()  # Mock DataFrame
            response = client.post("/api/data/upload-csv", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "dataset_id" in data
        assert isinstance(data["dataset_id"], str)
        assert data["cached"] is False

    def test_upload_csv_non_csv_file(self, client: TestClient):
        """POST /api/data/upload-csv rejects non-.csv files."""
        files = {"file": ("test.txt", io.BytesIO(b"not a csv"), "text/plain")}
        
        response = client.post("/api/data/upload-csv", files=files)
        assert response.status_code == 400
        assert "Only .csv files are accepted" in response.json()["detail"]

    def test_upload_csv_non_utf8_encoding(self, client: TestClient):
        """POST /api/data/upload-csv rejects non-UTF8 encoded files."""
        # Create non-UTF8 content
        csv_content = b"\xFF\xFEKey,Summary"  # Invalid UTF-8
        
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        response = client.post("/api/data/upload-csv", files=files)
        
        assert response.status_code == 400
        assert "UTF-8" in response.json()["detail"]

    def test_upload_csv_invalid_csv_format(self, client: TestClient):
        """POST /api/data/upload-csv rejects invalid CSV format."""
        csv_content = b"This is not valid CSV"
        
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        with patch("backend.reader.csv.read_from_string") as mock_read:
            mock_read.side_effect = Exception("CSV parsing failed")
            response = client.post("/api/data/upload-csv", files=files)
        
        assert response.status_code == 422
        assert "Could not parse CSV" in response.json()["detail"]

    def test_upload_csv_caching_same_content(self, client: TestClient):
        """POST /api/data/upload-csv caches uploads with same content."""
        csv_content = b"""Key,Summary
TEST-1,Issue 1"""
        
        files1 = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        files2 = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        with patch("backend.reader.csv.read_from_string") as mock_read:
            mock_df = MagicMock()
            mock_read.return_value = mock_df
            
            response1 = client.post("/api/data/upload-csv", files=files1)
            dataset_id_1 = response1.json()["dataset_id"]
            
            response2 = client.post("/api/data/upload-csv", files=files2)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response2.json()["cached"] is True
        assert response2.json()["dataset_id"] == dataset_id_1


class TestDataCacheClear:
    """Tests for DELETE /api/data/cache."""

    def test_clear_cache_empty(self, client: TestClient):
        """DELETE /api/data/cache returns 0 when no datasets exist."""
        response = client.delete("/api/data/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 0

    def test_clear_cache_deletes_all_datasets(self, client: TestClient, db_temp):
        """DELETE /api/data/cache deletes all datasets."""
        import sqlite3
        from backend import database
        
        # Create multiple datasets
        conn = database.get_db(db_temp)
        for i in range(3):
            data_service.create_dataset(conn, f"hash_{i}", "jira")
        conn.close()
        
        response = client.delete("/api/data/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 3

    def test_clear_cache_deleted_datasets_inaccessible(self, client: TestClient, db_temp):
        """After DELETE /api/data/cache, datasets are no longer accessible."""
        import sqlite3
        from backend import database
        
        # Create a dataset
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")
        conn.close()
        
        # Verify it exists
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        
        # Clear cache
        client.delete("/api/data/cache")
        
        # Now it should not be found
        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 404
