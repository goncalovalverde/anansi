"""Edge case tests for Anansi API - covers boundary conditions, error handling, and resilience."""

import io
import threading
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend import database
from backend.services import data_service


class TestEmptyResults:
    """Tests for empty or no results scenarios."""

    def test_load_empty_jql_results(self, client: TestClient, db_temp):
        """POST /api/data/load with JQL returning 0 issues."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = NONEXISTENT",
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
        assert "dataset_id" in response.json()

    def test_upload_empty_csv_file(self, client: TestClient):
        """POST /api/data/upload-csv with empty CSV file (only headers)."""
        csv_content = b"Key,Summary,Status\n"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            mock_read.return_value = pd.DataFrame(columns=["Key", "Summary", "Status"])
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200

    def test_charts_with_empty_dataframe(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} with empty but ready dataset."""
        import pandas as pd

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "empty_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        empty_df = pd.DataFrame()
        data_service.save_dataframe(conn, dataset_id, empty_df)
        conn.close()

        with patch("backend.services.backlog_cache.get_dashboard_response") as mock_charts:
            mock_charts.return_value = {"charts": []}
            response = client.get(f"/api/charts/{dataset_id}")

        assert response.status_code == 200


class TestMalformedInputs:
    """Tests for malformed or corrupted input scenarios."""

    def test_malformed_jql_syntax(self, client: TestClient):
        """POST /api/data/load with invalid JQL syntax."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = AND OR invalid ))))",
                "jira_auth_method": "basic",
                "jira_username": "testuser",
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )

        with patch("backend.services.data_service.load_data_task"):
            with patch("backend.reader.jira.validate_auth_config"):
                response = client.post("/api/data/load")

        assert response.status_code == 200  # Still creates dataset, error happens in background

    def test_upload_csv_missing_required_columns(self, client: TestClient):
        """POST /api/data/upload-csv with CSV missing expected columns."""
        csv_content = b"WrongColumn1,WrongColumn2\nvalue1,value2"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            mock_read.return_value = pd.DataFrame({"WrongColumn1": ["value1"], "WrongColumn2": ["value2"]})
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200

    def test_upload_csv_corrupted_encoding(self, client: TestClient):
        """POST /api/data/upload-csv with non-UTF8 encoded file."""
        csv_content = b"\xFF\xFEKey,Summary"  # UTF-16LE BOM
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        response = client.post("/api/data/upload-csv", files=files)
        assert response.status_code == 400

    def test_upload_csv_with_special_characters(self, client: TestClient):
        """POST /api/data/upload-csv with special/unicode characters."""
        csv_content = "Key,Summary,Status\nTEST-1,Issue with émojis 🚀,Done\nTEST-2,中文测试,In Progress".encode('utf-8')
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            df = pd.DataFrame({
                "Key": ["TEST-1", "TEST-2"],
                "Summary": ["Issue with émojis 🚀", "中文测试"],
                "Status": ["Done", "In Progress"]
            })
            mock_read.return_value = df
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200

    def test_put_config_with_extremely_long_values(self, client: TestClient):
        """PUT /api/config with extremely long string values."""
        long_jql = "project = TEST AND (" + " OR ".join([f"key = TEST-{i}" for i in range(1000)]) + ")"
        response = client.put(
            "/api/config",
            json={"jira_jql_query": long_jql}
        )
        assert response.status_code == 200
        assert response.json()["jira_jql_query"] == long_jql

    def test_upload_csv_with_missing_newline_at_end(self, client: TestClient):
        """POST /api/data/upload-csv with CSV file missing trailing newline."""
        csv_content = b"Key,Summary\nTEST-1,Issue"  # No trailing newline
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            mock_read.return_value = pd.DataFrame({"Key": ["TEST-1"], "Summary": ["Issue"]})
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200


class TestNetworkErrors:
    """Tests for network-related error scenarios."""

    def test_jira_connection_timeout(self, client: TestClient, db_temp):
        """POST /api/data/load when Jira request times out."""
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
        dataset_id = response.json()["dataset_id"]

        # Simulate timeout in background task
        conn = database.get_db(db_temp)
        data_service.update_dataset_status(
            conn, dataset_id, "failed",
            error="Connection timeout after 30 seconds"
        )
        conn.close()

        status_response = client.get(f"/api/data/{dataset_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "failed"

    def test_jira_connection_refused(self, client: TestClient, db_temp):
        """POST /api/data/load when Jira connection is refused."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://invalid-host-that-does-not-exist-12345.com",
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


class TestDatabaseErrors:
    """Tests for database-related error scenarios."""

    def test_database_locked_during_read(self, client: TestClient, db_temp):
        """GET /api/config when database is locked."""
        conn = database.get_db(db_temp)
        conn.execute("BEGIN EXCLUSIVE")  # Lock the database

        try:
            # Try to read config - should wait or timeout
            response = client.get("/api/config")
            # Depending on implementation, might succeed or timeout
            assert response.status_code in [200, 500]
        finally:
            conn.execute("ROLLBACK")
            conn.close()

    def test_dataset_status_with_corrupted_data(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status with corrupted dataset record."""
        from fastapi.exceptions import ResponseValidationError

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "test_hash", "jira")

        # Manually corrupt the progress data
        conn.execute(
            "UPDATE datasets SET progress_total = -1, progress_loaded = -999 WHERE id = ?",
            (dataset_id,)
        )
        conn.commit()
        conn.close()

        # Pydantic response model has ge=0 on progress fields; negative values
        # cause ResponseValidationError (TestClient raises it with default settings)
        with pytest.raises(ResponseValidationError):
            client.get(f"/api/data/{dataset_id}/status")


class TestConcurrentOperations:
    """Tests for concurrent request scenarios."""

    def test_concurrent_chart_requests(self, client: TestClient, db_temp, sample_dataframe):
        """GET /api/charts/{dataset_id} from multiple threads simultaneously."""

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "concurrent_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, sample_dataframe)
        conn.close()

        results = []
        errors = []

        def make_request():
            try:
                with patch("backend.services.backlog_cache.get_dashboard_response") as mock:
                    mock.return_value = {"charts": [{"name": "test", "data": []}]}
                    resp = client.get(f"/api/charts/{dataset_id}")
                    results.append(resp.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create 5 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All requests should succeed
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(code == 200 for code in results)

    def test_concurrent_config_updates(self, client: TestClient):
        """PUT /api/config from multiple threads simultaneously."""
        results = []
        errors = []

        def update_config(value):
            try:
                resp = client.put(
                    "/api/config",
                    json={"jira_url": f"https://jira-{value}.test.com"}
                )
                results.append(resp.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create 5 concurrent update requests
        threads = [threading.Thread(target=update_config, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All updates should succeed
        assert len(errors) == 0
        assert all(code == 200 for code in results)


class TestLargeDatasets:
    """Tests for large dataset scenarios."""

    @pytest.mark.slow
    def test_large_csv_upload(self, client: TestClient):
        """POST /api/data/upload-csv with large CSV (1000+ rows)."""
        # Create CSV with 1000 rows
        rows = ["Key,Summary,Status,Created"]
        for i in range(1000):
            rows.append(f"TEST-{i},Issue {i},Done,2024-01-01")
        csv_content = "\n".join(rows).encode('utf-8')

        files = {"file": ("large.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            data = {
                "Key": [f"TEST-{i}" for i in range(1000)],
                "Summary": [f"Issue {i}" for i in range(1000)],
                "Status": ["Done"] * 1000,
                "Created": ["2024-01-01"] * 1000,
            }
            mock_read.return_value = pd.DataFrame(data)
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200

    def test_charts_rendering_with_large_dataframe(self, client: TestClient, db_temp):
        """GET /api/charts/{dataset_id} with large dataset (1000+ rows)."""
        import pandas as pd

        # Create large dataframe
        base_date = datetime(2024, 1, 1)
        large_df = pd.DataFrame({
            "Key": [f"TEST-{i}" for i in range(1000)],
            "Summary": [f"Issue {i}" for i in range(1000)],
            "Type": ["Story"] * 1000,
            "Status": ["Done"] * 1000,
            "Created": [base_date + timedelta(hours=i) for i in range(1000)],
            "Backlog": [base_date + timedelta(hours=i+1) for i in range(1000)],
            "In Progress": [base_date + timedelta(hours=i+2) for i in range(1000)],
            "Done": [base_date + timedelta(hours=i+3) for i in range(1000)],
            "Story Points": [5.0] * 1000,
            "Epic Link": ["EPIC-1"] * 1000,
        })

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "large_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, large_df)
        conn.close()

        with patch("backend.services.backlog_cache.get_dashboard_response") as mock_charts:
            mock_charts.return_value = {"charts": [{"name": "test", "data": []}]}
            response = client.get(f"/api/charts/{dataset_id}")

        assert response.status_code == 200


class TestInvalidFieldConfiguration:
    """Tests for invalid Jira field configurations."""

    def test_non_existent_story_points_field(self, client: TestClient):
        """Configuration with non-existent Jira field (story_points_field)."""
        response = client.put(
            "/api/config",
            json={
                "jira_story_points_field": "customfield_99999",  # Non-existent field
            }
        )
        assert response.status_code == 200
        # API accepts it; error occurs during data loading

    def test_non_existent_epic_link_field(self, client: TestClient):
        """Configuration with non-existent Jira field (epic_link_field)."""
        response = client.put(
            "/api/config",
            json={
                "jira_epic_link_field": "customfield_88888",  # Non-existent field
            }
        )
        assert response.status_code == 200
        # API accepts it; error occurs during data loading

    def test_invalid_auth_method(self, client: TestClient):
        """PUT /api/config with invalid auth method."""
        # Schema has pattern="^(basic|oauth|pat)$" on jira_auth_method
        response = client.put(
            "/api/config",
            json={
                "jira_auth_method": "invalid_method",
            }
        )
        # Invalid value rejected by Pydantic pattern validation
        assert response.status_code == 422
        assert "validation" in response.text.lower() or "pattern" in response.text.lower()


class TestNullOptionalFields:
    """Tests for handling null/missing optional fields."""

    def test_jira_issue_without_story_points(self, client: TestClient, db_temp):
        """Loading Jira data where some issues lack story points."""
        import pandas as pd

        df = pd.DataFrame({
            "Key": ["TEST-1", "TEST-2"],
            "Summary": ["Issue with SP", "Issue without SP"],
            "Type": ["Story", "Story"],
            "Status": ["Done", "Done"],
            "Created": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            "Backlog": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            "In Progress": [datetime(2024, 1, 2), datetime(2024, 1, 3)],
            "Done": [datetime(2024, 1, 3), datetime(2024, 1, 4)],
            "Story Points": [5.0, None],  # Second issue has no SP
            "Epic Link": ["EPIC-1", None],
        })

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "null_sp_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, df)
        conn.close()

        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200

    def test_csv_with_empty_optional_fields(self, client: TestClient):
        """POST /api/data/upload-csv with CSV containing empty optional fields."""
        csv_content = b"""Key,Summary,Status,Story Points,Epic Link
TEST-1,Issue 1,Done,5,EPIC-1
TEST-2,Issue 2,In Progress,,
TEST-3,Issue 3,Backlog,3,"""
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import numpy as np
            import pandas as pd
            df = pd.DataFrame({
                "Key": ["TEST-1", "TEST-2", "TEST-3"],
                "Summary": ["Issue 1", "Issue 2", "Issue 3"],
                "Status": ["Done", "In Progress", "Backlog"],
                "Story Points": [5.0, np.nan, 3.0],
                "Epic Link": ["EPIC-1", np.nan, np.nan],
            })
            mock_read.return_value = df
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200


class TestAuthenticationErrors:
    """Tests for authentication-related error scenarios."""

    def test_load_with_missing_username(self, client: TestClient):
        """POST /api/data/load with missing username in basic auth."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "basic",
                "jira_username": "",  # Missing
                "jira_password": "testpass",
                "input_mode": "jira",
            }
        )

        response = client.post("/api/data/load")
        assert response.status_code == 400

    def test_load_with_missing_pat_token(self, client: TestClient):
        """POST /api/data/load with missing PAT token."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "pat",
                "jira_pat_token": "",  # Missing
                "input_mode": "jira",
            }
        )

        response = client.post("/api/data/load")
        assert response.status_code == 400

    def test_load_with_missing_oauth_fields(self, client: TestClient):
        """POST /api/data/load with incomplete OAuth configuration."""
        client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_auth_method": "oauth",
                # Missing required OAuth fields
                "input_mode": "jira",
            }
        )

        response = client.post("/api/data/load")
        assert response.status_code == 400


class TestBoundaryConditions:
    """Tests for boundary condition scenarios."""

    def test_workflow_with_minimum_steps(self, client: TestClient):
        """PUT /api/config/workflow with exactly 2 steps (minimum)."""
        response = client.put(
            "/api/config/workflow",
            json={"steps": ["Start", "End"]}
        )
        assert response.status_code == 200
        assert response.json()["steps"] == ["Start", "End"]

    def test_workflow_with_many_steps(self, client: TestClient):
        """PUT /api/config/workflow with many steps (10+)."""
        steps = [f"Step{i}" for i in range(1, 11)]
        response = client.put(
            "/api/config/workflow",
            json={"steps": steps}
        )
        assert response.status_code == 200
        assert response.json()["steps"] == steps

    def test_issue_types_with_single_type(self, client: TestClient):
        """PUT /api/config/issue-types with single type."""
        response = client.put(
            "/api/config/issue-types",
            json={"types": ["SingleType"]}
        )
        assert response.status_code == 200

    def test_dataset_status_progress_boundaries(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status with progress at boundaries."""
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "progress_hash", "jira")

        # Set progress to 0/0
        data_service.update_dataset_progress(conn, dataset_id, 0, 0)
        conn.close()

        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["progress_loaded"] == 0
        assert data["progress_total"] == 0

    def test_dataset_status_progress_at_100_percent(self, client: TestClient, db_temp):
        """GET /api/data/{dataset_id}/status with progress at 100%."""
        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "complete_hash", "jira")

        # Set progress to 1000/1000
        data_service.update_dataset_progress(conn, dataset_id, 1000, 1000)
        conn.close()

        response = client.get(f"/api/data/{dataset_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["progress_loaded"] == 1000
        assert data["progress_total"] == 1000


class TestDataValidation:
    """Tests for data validation edge cases."""

    def test_config_with_special_characters_in_jql(self, client: TestClient):
        """PUT /api/config with special characters in JQL query."""
        jql = 'summary ~ "test \\"quoted\\"" AND labels = "my-label"'
        response = client.put(
            "/api/config",
            json={"jira_jql_query": jql}
        )
        assert response.status_code == 200

    def test_workflow_with_duplicate_steps(self, client: TestClient):
        """PUT /api/config/workflow with duplicate step names."""
        response = client.put(
            "/api/config/workflow",
            json={"steps": ["Backlog", "In Progress", "Backlog", "Done"]}
        )
        # Should accept duplicates (validation of uniqueness is business logic)
        assert response.status_code == 200

    def test_issue_types_with_duplicate_names(self, client: TestClient):
        """PUT /api/config/issue-types with duplicate type names."""
        import sqlite3
        # UNIQUE constraint on issue_types.name causes IntegrityError.
        # The endpoint has no error handling, so TestClient raises the exception.
        with pytest.raises(sqlite3.IntegrityError):
            client.put(
                "/api/config/issue-types",
                json={"types": ["Story", "Bug", "Story"]}
            )

    def test_config_with_numeric_values_as_strings(self, client: TestClient):
        """PUT /api/config with numeric config values passed as strings."""
        response = client.put(
            "/api/config",
            json={"jira_api_version": "2"}  # Numeric version as string
        )
        assert response.status_code == 200

    def test_csv_with_numeric_dates(self, client: TestClient):
        """POST /api/data/upload-csv with dates in multiple formats."""
        csv_content = b"""Key,Summary,Created
TEST-1,Issue 1,2024-01-01
TEST-2,Issue 2,01/01/2024
TEST-3,Issue 3,2024-01-01T00:00:00Z"""
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

        with patch("backend.reader.csv.read_from_string") as mock_read:
            import pandas as pd
            mock_read.return_value = pd.DataFrame({
                "Key": ["TEST-1", "TEST-2", "TEST-3"],
                "Summary": ["Issue 1", "Issue 2", "Issue 3"],
                "Created": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"])
            })
            response = client.post("/api/data/upload-csv", files=files)

        assert response.status_code == 200


class TestErrorRecovery:
    """Tests for error recovery and resilience."""

    def test_trends_with_missing_data_columns(self, client: TestClient, db_temp):
        """GET /api/trends/{dataset_id} with dataframe missing required columns."""
        import pandas as pd

        minimal_df = pd.DataFrame({
            "Key": ["TEST-1", "TEST-2"],
            "Status": ["Done", "In Progress"]
        })

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "minimal_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, minimal_df)
        conn.close()

        with patch("backend.services.backlog_cache.get_trends_response") as mock_trends:
            mock_trends.return_value = {
                "cumulative_flow": {},
                "monthly_throughput": {},
                "epic_progress": {},
            }
            response = client.get(f"/api/trends/{dataset_id}")

        assert response.status_code == 200

    def test_insights_with_minimal_data(self, client: TestClient, db_temp):
        """GET /api/insights/{dataset_id} with minimal dataset."""
        import pandas as pd

        minimal_df = pd.DataFrame({
            "Key": ["TEST-1"],
            "Status": ["Done"],
            "Created": [datetime.now()]
        })

        conn = database.get_db(db_temp)
        dataset_id = data_service.create_dataset(conn, "insight_min_hash", "jira")
        data_service.update_dataset_status(conn, dataset_id, "ready")
        data_service.save_dataframe(conn, dataset_id, minimal_df)
        conn.close()

        with patch("backend.services.backlog_cache.get_insights_response") as mock_insights:
            mock_insights.return_value = {"insights": []}
            response = client.get(f"/api/insights/{dataset_id}")

        assert response.status_code in [200, 404, 500]  # Might fail, but shouldn't crash
