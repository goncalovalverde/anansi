"""Pytest configuration and shared fixtures for Anansi API tests."""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Add backend to path so we can import it
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from backend import database, main
from backend.dependencies import get_db


@pytest.fixture
def db_temp():
    """Temporary SQLite database for each test.
    
    Uses an in-memory database or temporary file.
    Database is initialized with schema and default data.
    """
    # Use temporary file instead of in-memory to support concurrent access
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Initialize database with schema
        database.init_db(db_path)
        
        yield db_path
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def client(db_temp):
    """FastAPI TestClient with test database dependency override.
    
    Overrides get_db dependency to use the test database.
    """
    def get_test_db():
        """Test database dependency override."""
        conn = database.get_db(db_temp)
        try:
            yield conn
        finally:
            conn.close()
    
    # Override the dependency
    main.app.dependency_overrides[get_db] = get_test_db
    
    # Create client
    test_client = TestClient(main.app)
    
    yield test_client
    
    # Clean up overrides
    main.app.dependency_overrides.clear()


@pytest.fixture
def sample_config():
    """Sample configuration data for tests."""
    return {
        "jira_url": "https://jira.example.com",
        "jira_jql_query": "project = TEST",
        "jira_auth_method": "basic",
        "jira_username": "testuser",
        "jira_password": "testpass",
        "jira_story_points_field": "customfield_10016",
        "jira_epic_link_field": "customfield_10014",
        "input_mode": "jira",
        "workflow_start_step": "In Progress",
    }


@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame with Jira-like data.
    
    Contains typical columns that Anansi processes:
    - Backlog: Date when moved to backlog
    - In Progress: Date when moved to in progress
    - Done: Date when completed
    - Story Points: Numeric story points
    - Epic Link: Epic name/link (expected by Backlog viewer)
    """
    import pandas as pd
    from datetime import datetime, timedelta
    
    base_date = datetime(2024, 1, 1)
    
    return pd.DataFrame({
        "Key": ["TEST-1", "TEST-2", "TEST-3", "TEST-4", "TEST-5"],
        "Summary": [
            "First issue",
            "Second issue",
            "Third issue",
            "Fourth issue",
            "Fifth issue",
        ],
        "Type": ["Story", "Story", "Bug", "Task", "Epic"],
        "Status": ["Done", "In Progress", "Backlog", "Done", "Backlog"],
        "Created": [
            base_date,
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
            base_date + timedelta(days=3),
            base_date + timedelta(days=4),
        ],
        "Backlog": [
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
            None,
            base_date + timedelta(days=3),
            None,
        ],
        "In Progress": [
            base_date + timedelta(days=2),
            base_date + timedelta(days=5),
            None,
            base_date + timedelta(days=4),
            None,
        ],
        "Done": [
            base_date + timedelta(days=5),
            None,
            None,
            base_date + timedelta(days=7),
            None,
        ],
        "Story Points": [5.0, 3.0, 2.0, 8.0, 0.0],
        "Epic Link": ["EPIC-1", "EPIC-1", "EPIC-2", "EPIC-2", "No Epic"],
    })


@pytest.fixture
def app():
    """FastAPI app instance."""
    return main.app
