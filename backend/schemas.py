"""Pydantic models for Anansi API request/response validation.

This module defines all request and response schemas for the API endpoints,
providing automatic validation, documentation, and type safety.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# CONFIG MODELS
# ============================================================================

class ConfigUpdate(BaseModel):
    """Configuration update request for JIRA and input settings.
    
    All fields are optional to support partial updates. When updating JIRA credentials:
    - For basic auth: provide jira_username and jira_password
    - For OAuth: provide jira_oauth_token, jira_oauth_token_secret, jira_oauth_consumer_key, jira_oauth_key_cert_file
    - For PAT: provide jira_pat_token
    
    Secret fields sent as empty string ('') or '***' are preserved (not overwritten).
    
    Examples:
        Update JIRA URL and JQL: {"jira_url": "https://...", "jira_jql_query": "project = TEST"}
        Switch to CSV mode: {"input_mode": "csv"}
        Update story points field: {"jira_story_points_field": "customfield_10016"}
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "jira_url": "https://jira.example.com",
            "jira_jql_query": "project = PROJ",
            "jira_auth_method": "basic",
            "jira_username": "user@example.com",
        }
    })

    jira_url: Optional[str] = Field(None, description="Jira instance URL")
    jira_jql_query: Optional[str] = Field(None, description="JQL query for fetching issues")
    jira_auth_method: Optional[str] = Field(
        None,
        description="Authentication method: 'basic', 'oauth', or 'pat'",
        pattern="^(basic|oauth|pat)$",
    )
    jira_username: Optional[str] = Field(None, description="Jira username (for basic auth)")
    jira_password: Optional[str] = Field(None, description="Jira password (for basic auth)")
    jira_pat_token: Optional[str] = Field(None, description="Jira Personal Access Token")
    jira_story_points_field: Optional[str] = Field(
        None, description="Custom field ID for story points"
    )
    jira_epic_link_field: Optional[str] = Field(None, description="Custom field ID for epic link")
    workflow_start_step: Optional[str] = Field(None, description="Start step in workflow")
    input_mode: Optional[str] = Field(
        None,
        description="Data input mode: 'jira' or 'csv'",
        pattern="^(jira|csv)$",
    )
    input_csv_file: Optional[str] = Field(None, description="Path to CSV file (if using CSV mode)")
    jira_oauth_token: Optional[str] = Field(None, description="OAuth token")
    jira_oauth_token_secret: Optional[str] = Field(None, description="OAuth token secret")
    jira_oauth_consumer_key: Optional[str] = Field(None, description="OAuth consumer key")
    jira_oauth_key_cert_file: Optional[str] = Field(None, description="OAuth key certificate file")
    jira_api_version: Optional[str] = Field(None, description="Jira API version")


class ConfigResponse(BaseModel):
    """Full configuration response - includes all stored config values.
    
    Secret fields (passwords, tokens) are masked as '***' in responses for security.
    Unset secret fields are returned as empty strings ('').
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "jira_url": "https://jira.example.com",
            "jira_jql_query": "project = PROJ",
            "jira_auth_method": "basic",
            "jira_username": "user@example.com",
            "jira_password": "***",
        }
    })

    jira_url: Optional[str] = None
    jira_jql_query: Optional[str] = None
    jira_auth_method: Optional[str] = None
    jira_username: Optional[str] = None
    jira_password: Optional[str] = None
    jira_pat_token: Optional[str] = None
    jira_story_points_field: Optional[str] = None
    jira_epic_link_field: Optional[str] = None
    workflow_start_step: Optional[str] = None
    input_mode: Optional[str] = None
    input_csv_file: Optional[str] = None
    jira_oauth_token: Optional[str] = None
    jira_oauth_token_secret: Optional[str] = None
    jira_oauth_consumer_key: Optional[str] = None
    jira_oauth_key_cert_file: Optional[str] = None
    jira_api_version: Optional[str] = None


# ============================================================================
# WORKFLOW MODELS
# ============================================================================


class WorkflowUpdate(BaseModel):
    """Workflow step configuration for issue status tracking.
    
    Steps define the pipeline from creation to completion (e.g., Backlog → In Progress → Done).
    Minimum 2 steps required. The last step is treated as 'Done' for cycle time calculations.
    Steps must be ordered from initial state to final completion state.
    
    Examples:
        Two-step: ["Backlog", "Done"]
        Multi-step: ["Backlog", "In Progress", "Review", "Done"]
        Extended: ["Backlog", "To Do", "In Progress", "Code Review", "Testing", "Ready", "Done"]
    """

    model_config = ConfigDict(json_schema_extra={"example": {"steps": ["To Do", "In Progress", "Done"]}})

    steps: List[str] = Field(..., min_length=2, description="List of workflow steps (at least 2)")


class WorkflowResponse(BaseModel):
    """Workflow response."""

    model_config = ConfigDict(json_schema_extra={"example": {"steps": ["To Do", "In Progress", "Done"]}})

    steps: List[str] = Field(..., description="List of workflow steps")


# ============================================================================
# ISSUE TYPES MODELS
# ============================================================================


class IssueTypesUpdate(BaseModel):
    """Issue types configuration for filtering and tracking.
    
    Specifies which issue type names from JIRA should be tracked and displayed.
    At least 1 type required. Common types include Story, Bug, Task, Epic, Sub-task.
    
    Examples:
        Track stories and bugs: ["Story", "Bug"]
        Track all types: ["Story", "Bug", "Task", "Epic"]
        Track epics only: ["Epic"]
    """

    model_config = ConfigDict(json_schema_extra={"example": {"types": ["Story", "Bug", "Task"]}})

    types: List[str] = Field(..., min_length=1, description="List of issue type names (at least 1)")


class IssueTypesResponse(BaseModel):
    """Issue types response."""

    model_config = ConfigDict(json_schema_extra={"example": {"types": ["Story", "Bug", "Task"]}})

    types: List[str] = Field(..., description="List of issue type names")


# ============================================================================
# TEST CONNECTION MODELS
# ============================================================================


class TestConnectionRequest(BaseModel):
    """Test connection request with optional JIRA configuration overrides.
    
    Used to validate JIRA connectivity before saving configuration. All fields are optional
    and will override corresponding values from the current config for the test.
    If not provided, current saved configuration will be used.
    
    Examples:
        Test basic auth: {"jira_url": "https://jira.example.com", "jira_username": "user", "jira_password": "pass"}
        Test with override URL: {"jira_url": "https://new-jira.example.com"}
        Test current config: {} (empty request body)
    """

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "jira_url": "https://jira.example.com",
            "jira_jql_query": "project = PROJ",
            "jira_auth_method": "basic",
            "jira_username": "user@example.com",
        }
    })

    jira_url: Optional[str] = Field(None, description="Jira instance URL")
    jira_jql_query: Optional[str] = Field(None, description="JQL query for fetching issues")
    jira_auth_method: Optional[str] = Field(
        None,
        description="Authentication method: 'basic', 'oauth', or 'pat'",
        pattern="^(basic|oauth|pat)$",
    )
    jira_username: Optional[str] = Field(None, description="Jira username (for basic auth)")
    jira_password: Optional[str] = Field(None, description="Jira password (for basic auth)")
    jira_pat_token: Optional[str] = Field(None, description="Jira Personal Access Token")
    jira_oauth_token: Optional[str] = Field(None, description="OAuth token")
    jira_oauth_token_secret: Optional[str] = Field(None, description="OAuth token secret")
    jira_oauth_consumer_key: Optional[str] = Field(None, description="OAuth consumer key")
    jira_oauth_key_cert_file: Optional[str] = Field(None, description="OAuth key certificate file")
    jira_api_version: Optional[str] = Field(None, description="Jira API version")


class TestConnectionResponse(BaseModel):
    """Test connection response."""

    model_config = ConfigDict(json_schema_extra={
        "examples": [
            {"success": True},
            {"success": False, "error": "Invalid credentials"},
        ]
    })

    success: bool = Field(..., description="Whether connection was successful")
    error: Optional[str] = Field(None, description="Error message if connection failed")


# ============================================================================
# JIRA API RESPONSE MODELS
# ============================================================================


class JiraStatusesResponse(BaseModel):
    """Response containing available Jira statuses."""

    model_config = ConfigDict(json_schema_extra={"example": {"statuses": ["To Do", "In Progress", "Done"]}})

    statuses: List[str] = Field(..., description="List of available status names")


class ProjectReference(BaseModel):
    """Reference to a Jira project."""

    key: str = Field(..., description="Project key")
    name: str = Field(..., description="Project name")


class JiraProjectsResponse(BaseModel):
    """Response containing accessible Jira projects."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "projects": [
                {"key": "PROJ", "name": "My Project"},
                {"key": "OTHER", "name": "Other Project"},
            ]
        }
    })

    projects: List[ProjectReference] = Field(..., description="List of accessible projects")


class JiraIssueTypesResponse(BaseModel):
    """Response containing available Jira issue types."""

    model_config = ConfigDict(json_schema_extra={"example": {"issue_types": ["Story", "Bug", "Task"]}})

    issue_types: List[str] = Field(..., description="List of available issue type names")


class FieldDefinition(BaseModel):
    """Definition of a Jira custom field."""

    id: str = Field(..., description="Field ID (e.g., customfield_10001)")
    name: str = Field(..., description="Field name")


class JiraFieldsResponse(BaseModel):
    """Response containing field detection results and all custom fields."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "story_points": [{"id": "customfield_10001", "name": "Story Points"}],
            "epic_link": [{"id": "customfield_10002", "name": "Epic Link"}],
            "all_custom_fields": [
                {"id": "customfield_10001", "name": "Story Points"},
                {"id": "customfield_10002", "name": "Epic Link"},
            ],
        }
    })

    story_points: List[FieldDefinition] = Field(
        ..., description="Candidate fields for story points"
    )
    epic_link: List[FieldDefinition] = Field(
        ..., description="Candidate fields for epic link"
    )
    all_custom_fields: List[FieldDefinition] = Field(
        ..., description="All custom fields available"
    )


# ============================================================================
# DATA MODELS
# ============================================================================


class DatasetResponse(BaseModel):
    """Response when loading or uploading a dataset."""

    model_config = ConfigDict(json_schema_extra={"example": {"dataset_id": "abc123def456", "cached": False}})

    dataset_id: str = Field(..., description="Unique identifier for the dataset")
    cached: bool = Field(..., description="Whether this is a cached dataset")


class DatasetStatusResponse(BaseModel):
    """Response containing dataset loading status."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "loading",
            "error": None,
            "progress_loaded": 50,
            "progress_total": 100,
        }
    })

    status: str = Field(
        ...,
        description="Dataset status: 'loading', 'ready', or 'error'",
    )
    error: Optional[str] = Field(None, description="Error message if status is 'error'")
    progress_loaded: int = Field(
        ..., ge=0, description="Number of items loaded so far"
    )
    progress_total: int = Field(
        ..., ge=0, description="Total number of items to load (0 if unknown)"
    )


# ============================================================================
# CACHE CLEAR MODELS
# ============================================================================


class CacheClearResponse(BaseModel):
    """Response when clearing the dataset cache."""

    model_config = ConfigDict(json_schema_extra={"example": {"deleted": 5}})

    deleted: int = Field(..., ge=0, description="Number of cached datasets deleted")

