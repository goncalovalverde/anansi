"""Tests for the /api/config endpoints."""

import pytest
from fastapi.testclient import TestClient
import sqlite3


class TestConfigRead:
    """Tests for GET /api/config."""

    def test_get_config_returns_all_config(self, client: TestClient):
        """GET /api/config returns all configuration with correct types."""
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        
        # Check that all expected keys are present
        expected_keys = {
            "jira_url", "jira_jql_query", "jira_auth_method",
            "jira_username", "jira_password", "jira_api_version",
            "input_mode", "input_csv_file"
        }
        assert expected_keys.issubset(set(data.keys()))

    def test_get_config_masks_secrets(self, client: TestClient):
        """GET /api/config masks secret keys as '***' or ''."""
        # Set a password
        client.put(
            "/api/config",
            json={"jira_password": "mysecretpass"}
        )
        
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        
        # Secret should be masked
        assert data["jira_password"] == "***"

    def test_get_config_empty_secret_as_empty_string(self, client: TestClient):
        """GET /api/config returns empty string for empty secrets."""
        response = client.get("/api/config")
        data = response.json()
        
        # Unset secret should be empty string
        assert data["jira_password"] == ""

    def test_get_config_with_slash(self, client: TestClient):
        """GET /api/config/ (with trailing slash) also works."""
        response = client.get("/api/config/")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)


class TestConfigWrite:
    """Tests for PUT /api/config."""

    def test_put_config_updates_single_key(self, client: TestClient):
        """PUT /api/config updates a valid config key."""
        response = client.put(
            "/api/config",
            json={"jira_url": "https://test.jira.com"}
        )
        assert response.status_code == 200
        assert response.json()["jira_url"] == "https://test.jira.com"

    def test_put_config_persists_changes(self, client: TestClient):
        """Changes made via PUT are returned in subsequent GET."""
        client.put(
            "/api/config",
            json={"jira_url": "https://persistent.jira.com"}
        )
        
        response = client.get("/api/config")
        assert response.json()["jira_url"] == "https://persistent.jira.com"

    def test_put_config_updates_multiple_keys(self, client: TestClient):
        """PUT /api/config can update multiple keys in one request."""
        response = client.put(
            "/api/config",
            json={
                "jira_url": "https://jira.test.com",
                "jira_jql_query": "project = TEST",
                "jira_username": "testuser",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["jira_url"] == "https://jira.test.com"
        assert data["jira_jql_query"] == "project = TEST"
        assert data["jira_username"] == "testuser"

    def test_put_config_skips_invalid_keys(self, client: TestClient):
        """PUT /api/config ignores keys not in _ALLOWED_CONFIG_KEYS."""
        response = client.put(
            "/api/config",
            json={
                "jira_url": "https://valid.jira.com",
                "invalid_key": "should_be_ignored",
                "another_bad_key": "also_ignored",
            }
        )
        assert response.status_code == 200
        # Valid key should be updated
        assert response.json()["jira_url"] == "https://valid.jira.com"
        # Invalid keys should not appear in response
        assert "invalid_key" not in response.json()
        assert "another_bad_key" not in response.json()

    def test_put_config_saves_non_secret_values(self, client: TestClient):
        """PUT /api/config saves non-secret values."""
        client.put(
            "/api/config",
            json={"jira_auth_method": "pat"}
        )
        
        response = client.get("/api/config")
        assert response.json()["jira_auth_method"] == "pat"

    def test_put_config_saves_secret_values(self, client: TestClient):
        """PUT /api/config saves actual secret values (not empty/masked)."""
        client.put(
            "/api/config",
            json={"jira_pat_token": "secret_token_value"}
        )
        
        # Verify via GET (which masks secrets)
        response = client.get("/api/config")
        assert response.json()["jira_pat_token"] == "***"

    def test_put_config_ignores_empty_secret(self, client: TestClient):
        """PUT /api/config doesn't overwrite secrets when passed '' or '***'."""
        # Set initial secret
        client.put(
            "/api/config",
            json={"jira_password": "initial_secret"}
        )
        
        # Try to update with empty string (should be ignored)
        client.put(
            "/api/config",
            json={"jira_password": ""}
        )
        
        # Try to update with masked value (should be ignored)
        client.put(
            "/api/config",
            json={"jira_password": "***"}
        )
        
        # Secret should remain unchanged (masked as ***)
        response = client.get("/api/config")
        assert response.json()["jira_password"] == "***"

    def test_put_config_with_slash(self, client: TestClient):
        """PUT /api/config/ (with trailing slash) also works."""
        response = client.put(
            "/api/config/",
            json={"jira_url": "https://test.com"}
        )
        assert response.status_code == 200
        assert response.json()["jira_url"] == "https://test.com"


class TestWorkflow:
    """Tests for workflow endpoints."""

    def test_get_workflow_returns_default_steps(self, client: TestClient):
        """GET /api/config/workflow returns default workflow steps."""
        response = client.get("/api/config/workflow")
        assert response.status_code == 200
        data = response.json()
        assert "steps" in data
        assert data["steps"] == ["Backlog", "In Progress", "Done"]

    def test_put_workflow_updates_steps(self, client: TestClient):
        """PUT /api/config/workflow updates workflow steps."""
        response = client.put(
            "/api/config/workflow",
            json={"steps": ["To Do", "Doing", "Review", "Done"]}
        )
        assert response.status_code == 200
        assert response.json()["steps"] == ["To Do", "Doing", "Review", "Done"]

    def test_put_workflow_persists_changes(self, client: TestClient):
        """Workflow changes persist across requests."""
        new_steps = ["Start", "Middle", "End"]
        client.put(
            "/api/config/workflow",
            json={"steps": new_steps}
        )
        
        response = client.get("/api/config/workflow")
        assert response.json()["steps"] == new_steps

    def test_put_workflow_rejects_non_list(self, client: TestClient):
        """PUT /api/config/workflow rejects non-list values."""
        response = client.put(
            "/api/config/workflow",
            json={"steps": "not a list"}
        )
        assert response.status_code == 422  # Validation error

    def test_put_workflow_rejects_single_step(self, client: TestClient):
        """PUT /api/config/workflow requires minimum 2 steps."""
        response = client.put(
            "/api/config/workflow",
            json={"steps": ["OnlyOne"]}
        )
        assert response.status_code == 422  # Validation error

    def test_put_workflow_with_many_steps(self, client: TestClient):
        """PUT /api/config/workflow accepts many steps."""
        steps = ["Step1", "Step2", "Step3", "Step4", "Step5"]
        response = client.put(
            "/api/config/workflow",
            json={"steps": steps}
        )
        assert response.status_code == 200
        assert response.json()["steps"] == steps


class TestIssueTypes:
    """Tests for issue types endpoints."""

    def test_get_issue_types_returns_default_types(self, client: TestClient):
        """GET /api/config/issue-types returns default issue types."""
        response = client.get("/api/config/issue-types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert data["types"] == ["Story", "Bug", "Task", "Epic"]

    def test_put_issue_types_updates_types(self, client: TestClient):
        """PUT /api/config/issue-types updates issue types."""
        response = client.put(
            "/api/config/issue-types",
            json={"types": ["Feature", "Defect", "Improvement"]}
        )
        assert response.status_code == 200
        assert response.json()["types"] == ["Feature", "Defect", "Improvement"]

    def test_put_issue_types_persists_changes(self, client: TestClient):
        """Issue type changes persist across requests."""
        new_types = ["CustomType1", "CustomType2"]
        client.put(
            "/api/config/issue-types",
            json={"types": new_types}
        )
        
        response = client.get("/api/config/issue-types")
        assert response.json()["types"] == new_types

    def test_put_issue_types_rejects_non_list(self, client: TestClient):
        """PUT /api/config/issue-types rejects non-list values."""
        response = client.put(
            "/api/config/issue-types",
            json={"types": "not a list"}
        )
        assert response.status_code == 422

    def test_put_issue_types_rejects_empty_list(self, client: TestClient):
        """PUT /api/config/issue-types requires at least 1 type."""
        response = client.put(
            "/api/config/issue-types",
            json={"types": []}
        )
        assert response.status_code == 422

    def test_put_issue_types_with_single_type(self, client: TestClient):
        """PUT /api/config/issue-types accepts single type."""
        response = client.put(
            "/api/config/issue-types",
            json={"types": ["OnlyType"]}
        )
        assert response.status_code == 200
        assert response.json()["types"] == ["OnlyType"]

    def test_put_issue_types_with_many_types(self, client: TestClient):
        """PUT /api/config/issue-types accepts many types."""
        types = ["Type1", "Type2", "Type3", "Type4", "Type5"]
        response = client.put(
            "/api/config/issue-types",
            json={"types": types}
        )
        assert response.status_code == 200
        assert response.json()["types"] == types
