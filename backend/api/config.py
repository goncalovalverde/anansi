import sqlite3
from fastapi import APIRouter, Depends, HTTPException

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import services.config_service as config_service

router = APIRouter(prefix="/api/config", tags=["config"])


def get_db():
    conn = database.get_db()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/")
@router.get("")
def read_config(db: sqlite3.Connection = Depends(get_db)):
    return config_service.get_config(db)


@router.put("/")
@router.put("")
def write_config(updates: dict, db: sqlite3.Connection = Depends(get_db)):
    config_service.set_config(db, updates)
    return config_service.get_config(db)


@router.get("/workflow")
def read_workflow(db: sqlite3.Connection = Depends(get_db)):
    return {"steps": config_service.get_workflow(db)}


@router.put("/workflow")
def write_workflow(body: dict, db: sqlite3.Connection = Depends(get_db)):
    steps = body.get("steps")
    if not isinstance(steps, list):
        raise HTTPException(status_code=400, detail="'steps' must be a list")
    config_service.set_workflow(db, steps)
    return {"steps": config_service.get_workflow(db)}


@router.get("/issue-types")
def read_issue_types(db: sqlite3.Connection = Depends(get_db)):
    return {"types": config_service.get_issue_types(db)}


@router.put("/issue-types")
def write_issue_types(body: dict, db: sqlite3.Connection = Depends(get_db)):
    types = body.get("types")
    if not isinstance(types, list):
        raise HTTPException(status_code=400, detail="'types' must be a list")
    config_service.set_issue_types(db, types)
    return {"types": config_service.get_issue_types(db)}


def _merge_overrides(jira_config: dict, overrides: dict) -> dict:
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
    result = dict(jira_config)
    result["oauth"] = dict(jira_config.get("oauth", {}))

    for form_key, cfg_key in plain_map.items():
        val = overrides.get(form_key)
        if val is None:
            continue
        if "." in cfg_key:
            section, field = cfg_key.split(".", 1)
            result[section][field] = val
        else:
            result[cfg_key] = val

    for form_key, cfg_key in secret_map.items():
        val = overrides.get(form_key)
        if val is None or val in ("", "***"):
            continue
        if "." in cfg_key:
            section, field = cfg_key.split(".", 1)
            result[section][field] = val
        else:
            result[cfg_key] = val

    return result


@router.post("/test-connection")
def test_connection(body: dict = None, db: sqlite3.Connection = Depends(get_db)):
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db, cache=False)
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


@router.post("/jira-statuses")
def get_jira_statuses(body: dict = None, db: sqlite3.Connection = Depends(get_db)):
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db, cache=False)
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


@router.post("/jira-projects")
def get_jira_projects(body: dict = None, db: sqlite3.Connection = Depends(get_db)):
    """Return list of Jira projects accessible with current credentials."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db, cache=False)
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


@router.post("/jira-issue-types")
def get_jira_issue_types(body: dict = None, db: sqlite3.Connection = Depends(get_db)):
    """Return all issue types available in the connected Jira instance."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db, cache=False)
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


@router.post("/jira-fields")
def get_jira_fields(body: dict = None, db: sqlite3.Connection = Depends(get_db)):
    """Return custom fields that likely map to story points or epic link."""
    import reader.jira as jira_reader

    jira_config = config_service.build_jira_config(db, cache=False)
    if body:
        jira_config = _merge_overrides(jira_config, body)

    try:
        jr = jira_reader.Jira(jira_config, [], database.DB_PATH)
        jira_instance = jr.get_jira_instance()
        fields = jira_instance.fields()
        story_candidates = [
            {"id": f["id"], "name": f["name"]}
            for f in fields
            if any(kw in f["name"].lower() for kw in ("story point", "story_point", "points", "sp"))
            and f["id"].startswith("customfield_")
        ]
        epic_candidates = [
            {"id": f["id"], "name": f["name"]}
            for f in fields
            if any(kw in f["name"].lower() for kw in ("epic link", "epic_link", "epic name", "parent epic"))
            and f["id"].startswith("customfield_")
        ]
        return {"story_points": story_candidates, "epic_link": epic_candidates}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch fields: {exc}")


