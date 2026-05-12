import sqlite3
import logging
from fastapi import APIRouter, Depends, HTTPException

from .. import database
from ..services import config_service
from ..dependencies import get_db
from ..reader import jira as jira_reader
from .. import schemas

router = APIRouter(prefix="/api/config", tags=["config"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=schemas.ConfigResponse)
@router.get("", response_model=schemas.ConfigResponse)
def read_config(db: sqlite3.Connection = Depends(get_db)):
    """Get current configuration."""
    return config_service.get_config(db)


@router.put("/", response_model=schemas.ConfigResponse)
@router.put("", response_model=schemas.ConfigResponse)
def write_config(
    updates: schemas.ConfigUpdate, db: sqlite3.Connection = Depends(get_db)
):
    """Update configuration with partial or full config updates."""
    config_service.set_config(db, updates.model_dump(exclude_none=True))
    return config_service.get_config(db)


@router.get("/workflow", response_model=schemas.WorkflowResponse)
def read_workflow(db: sqlite3.Connection = Depends(get_db)):
    """Get workflow steps."""
    return {"steps": config_service.get_workflow(db)}


@router.put("/workflow", response_model=schemas.WorkflowResponse)
def write_workflow(
    body: schemas.WorkflowUpdate, db: sqlite3.Connection = Depends(get_db)
):
    """Update workflow steps (minimum 2 steps required)."""
    config_service.set_workflow(db, body.steps)
    return {"steps": config_service.get_workflow(db)}


@router.get("/issue-types", response_model=schemas.IssueTypesResponse)
def read_issue_types(db: sqlite3.Connection = Depends(get_db)):
    """Get configured issue types."""
    return {"types": config_service.get_issue_types(db)}


@router.put("/issue-types", response_model=schemas.IssueTypesResponse)
def write_issue_types(
    body: schemas.IssueTypesUpdate, db: sqlite3.Connection = Depends(get_db)
):
    """Update issue types (minimum 1 type required)."""
    config_service.set_issue_types(db, body.types)
    return {"types": config_service.get_issue_types(db)}


@router.get("/chart-thresholds")
def read_chart_thresholds(db: sqlite3.Connection = Depends(get_db)):
    """Get current chart thresholds (defaults merged with overrides)."""
    return config_service.get_chart_thresholds(db)


@router.get("/chart-thresholds/defaults")
def read_chart_threshold_defaults():
    """Get built-in default chart thresholds."""
    return config_service.get_chart_threshold_defaults()


@router.put("/chart-thresholds")
def write_chart_thresholds(
    body: dict, db: sqlite3.Connection = Depends(get_db)
):
    """Update chart thresholds (partial update supported)."""
    config_service.set_chart_thresholds(db, body)
    return config_service.get_chart_thresholds(db)


@router.delete("/chart-thresholds")
def reset_chart_thresholds(db: sqlite3.Connection = Depends(get_db)):
    """Reset all chart thresholds to defaults."""
    return config_service.reset_chart_thresholds(db)


def _merge_overrides(jira_config: dict, overrides: schemas.TestConnectionRequest) -> dict:
    """Merge form-submitted overrides into a jira_config dict.

    Secret fields sent as '' or '***' are ignored so stored secrets are kept.
    """
    secret_map = {
        "jira_password": "password",
        "jira_pat_token": "pat_token",
        "jira_oauth_token": "oauth.token",
        "jira_oauth_token_secret": "oauth.token_secret",
    }
    plain_map = {
        "jira_url": "url",
        "jira_jql_query": "jql_query",
        "jira_auth_method": "auth_method",
        "jira_api_version": "api_version",
        "jira_username": "username",
        "jira_story_points_field": "story_points_field",
        "jira_epic_link_field": "epic_link_field",
        "jira_oauth_consumer_key": "oauth.consumer_key",
        "jira_oauth_key_cert_file": "oauth.key_cert_file",
    }
    
    # Convert Pydantic model to dict, excluding None values
    overrides_dict = overrides.model_dump(exclude_none=True)
    result = dict(jira_config)
    result["oauth"] = dict(jira_config.get("oauth", {}))

    for form_key, cfg_key in plain_map.items():
        val = overrides_dict.get(form_key)
        if val is None:
            continue
        if "." in cfg_key:
            section, field = cfg_key.split(".", 1)
            result[section][field] = val
        else:
            result[cfg_key] = val

    for form_key, cfg_key in secret_map.items():
        val = overrides_dict.get(form_key)
        if val is None or val in ("", "***"):
            continue
        if "." in cfg_key:
            section, field = cfg_key.split(".", 1)
            result[section][field] = val
        else:
            result[cfg_key] = val

    return result


@router.post("/test-connection", response_model=schemas.TestConnectionResponse)
def test_connection(
    body: schemas.TestConnectionRequest = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Test connection to Jira with current or provided config."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db)
    if body:
        jira_config = _merge_overrides(jira_config, body)
    workflow = config_service.get_workflow(db)

    try:
        jr = jira_reader.Jira(jira_config, workflow, database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        jira_instance.search_issues(jira_config["jql_query"], maxResults=1)
        return {"success": True}
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/jira-statuses", response_model=schemas.JiraStatusesResponse)
def get_jira_statuses(
    body: schemas.TestConnectionRequest = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Get list of available statuses from Jira instance."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db)
    if body:
        jira_config = _merge_overrides(jira_config, body)
    workflow = config_service.get_workflow(db)

    try:
        jr = jira_reader.Jira(jira_config, workflow, database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        statuses = jira_instance.statuses()
        return {"statuses": sorted(set(s.name for s in statuses))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch statuses: {exc}")


@router.post("/jira-projects", response_model=schemas.JiraProjectsResponse)
def get_jira_projects(
    body: schemas.TestConnectionRequest = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return list of Jira projects accessible with current credentials."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db)
    if body:
        jira_config = _merge_overrides(jira_config, body)

    try:
        jr = jira_reader.Jira(jira_config, [], database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        projects = jira_instance.projects()
        return {
            "projects": [
                {"key": p.key, "name": p.name}
                for p in sorted(projects, key=lambda p: p.name)
            ]
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch projects: {exc}")


@router.post("/jira-issue-types", response_model=schemas.JiraIssueTypesResponse)
def get_jira_issue_types(
    body: schemas.TestConnectionRequest = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return all issue types available in the connected Jira instance."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db)
    if body:
        jira_config = _merge_overrides(jira_config, body)

    try:
        jr = jira_reader.Jira(jira_config, [], database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        types = jira_instance.issue_types()
        return {"issue_types": sorted(set(t.name for t in types))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch issue types: {exc}")


@router.post("/jira-fields", response_model=schemas.JiraFieldsResponse)
def get_jira_fields(
    body: schemas.TestConnectionRequest = None,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return custom fields that likely map to story points or epic link."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db)
    if body:
        jira_config = _merge_overrides(jira_config, body)

    try:
        jr = jira_reader.Jira(jira_config, [], database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        fields = jira_instance.fields()

        custom_fields = [f for f in fields if f["id"].startswith("customfield_")]
        logger.debug("Available custom fields: %s", [(f["id"], f["name"]) for f in custom_fields])

        story_candidates = config_service.detect_story_point_fields(fields)
        epic_candidates = config_service.detect_epic_link_fields(fields)

        logger.info(
            "Field detection: story_points=%s epic_link=%s",
            [f["id"] for f in story_candidates],
            [f["id"] for f in epic_candidates],
        )
        return {
            "story_points": story_candidates,
            "epic_link": epic_candidates,
            "all_custom_fields": custom_fields,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch fields: {exc}")

