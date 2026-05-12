import sqlite3
from .. import database

SECRET_KEYS = database.SECRET_KEYS

_ALLOWED_CONFIG_KEYS = {
    "jira_url",
    "jira_jql_query",
    "jira_auth_method",
    "jira_username",
    "jira_password",
    "jira_story_points_field",
    "jira_epic_link_field",
    "jira_oauth_token",
    "jira_oauth_token_secret",
    "jira_oauth_consumer_key",
    "jira_oauth_key_cert_file",
    "jira_pat_token",
    "jira_api_version",
    "input_mode",
    "input_csv_file",
    "workflow_start_step",
}


def get_config(db: sqlite3.Connection) -> dict:
    rows = db.execute("SELECT key, value FROM config").fetchall()
    result = {}
    for row in rows:
        key, value = row["key"], row["value"]
        if key in SECRET_KEYS:
            result[key] = "***" if value else ""
        else:
            result[key] = value
    return result


def get_raw_config(db: sqlite3.Connection) -> dict:
    rows = db.execute("SELECT key, value FROM config").fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_config(db: sqlite3.Connection, updates: dict) -> None:
    for key, value in updates.items():
        if key not in _ALLOWED_CONFIG_KEYS:
            continue
        if key in SECRET_KEYS and value in ("", "***"):
            continue
        db.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    db.commit()


def get_workflow(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT step FROM workflow_steps ORDER BY position"
    ).fetchall()
    return [row["step"] for row in rows]


def set_workflow(db: sqlite3.Connection, steps: list[str]) -> None:
    db.execute("DELETE FROM workflow_steps")
    db.executemany(
        "INSERT INTO workflow_steps (position, step) VALUES (?, ?)",
        enumerate(steps),
    )
    db.commit()


def get_issue_types(db: sqlite3.Connection) -> list[str]:
    rows = db.execute("SELECT name FROM issue_types ORDER BY id").fetchall()
    return [row["name"] for row in rows]


def set_issue_types(db: sqlite3.Connection, types: list[str]) -> None:
    db.execute("DELETE FROM issue_types")
    db.executemany(
        "INSERT INTO issue_types (name) VALUES (?)",
        [(t,) for t in types],
    )
    db.commit()


def build_jira_config(db: sqlite3.Connection) -> dict:
    """Build the jira config dict from the database."""
    raw = get_raw_config(db)
    return {
        "url": raw.get("jira_url", ""),
        "jql_query": raw.get("jira_jql_query", ""),
        "auth_method": raw.get("jira_auth_method", "basic"),
        "api_version": raw.get("jira_api_version", "2"),
        "username": raw.get("jira_username", ""),
        "password": raw.get("jira_password", ""),
        "pat_token": raw.get("jira_pat_token", ""),
        "story_points_field": raw.get("jira_story_points_field", ""),
        "epic_link_field": raw.get("jira_epic_link_field", ""),
        "oauth": {
            "token": raw.get("jira_oauth_token", ""),
            "token_secret": raw.get("jira_oauth_token_secret", ""),
            "consumer_key": raw.get("jira_oauth_consumer_key", ""),
            "key_cert_file": raw.get("jira_oauth_key_cert_file", ""),
        },
    }


def detect_story_point_fields(fields: list[dict]) -> list[dict]:
    """Identify custom fields likely to represent story points.

    Matches on field name containing 'story point' or 'storypoint' (case-insensitive).
    Short tokens like 'sp' or 'points' are excluded as they match unrelated fields.
    """
    def _is_sp_name(name: str) -> bool:
        n = name.lower()
        return "story point" in n or "storypoint" in n

    return [
        {"id": f["id"], "name": f["name"]}
        for f in fields
        if f["id"].startswith("customfield_") and _is_sp_name(f.get("name", ""))
    ]


def detect_epic_link_fields(fields: list[dict]) -> list[dict]:
    """Identify custom fields likely to represent epic links.

    Matches on well-known Jira schema types first (locale-independent),
    then falls back to keyword matching on the field name.
    Returns schema-matched fields first (most reliable), name-matched second.
    """
    EPIC_SCHEMA_TYPES = ("gh-epic-link", "gh-epic-label", "greenhopper-epic")

    candidates = [
        f for f in fields
        if f["id"].startswith("customfield_")
        and (
            any(t in f.get("schema", {}).get("custom", "").lower() for t in EPIC_SCHEMA_TYPES)
            or any(kw in f.get("name", "").lower() for kw in (
                "epic link", "epic_link", "epic name", "parent epic", "epic"
            ))
        )
    ]

    def _sort_key(f: dict) -> int:
        schema_custom = f.get("schema", {}).get("custom", "").lower()
        return 0 if any(t in schema_custom for t in EPIC_SCHEMA_TYPES) else 1

    candidates.sort(key=_sort_key)
    return [{"id": f["id"], "name": f["name"]} for f in candidates]


def build_reader_config(db: sqlite3.Connection) -> dict:
    raw = get_raw_config(db)
    workflow = get_workflow(db)
    issue_types = get_issue_types(db)

    stored_start = raw.get("workflow_start_step", "")
    if stored_start and stored_start in workflow:
        start_step = stored_start
    else:
        start_step = workflow[1] if len(workflow) > 1 else (workflow[0] if workflow else "In Progress")

    # Collect chart threshold overrides (keys prefixed with "chart_")
    chart_thresholds = {
        k[len("chart_"):]: v
        for k, v in raw.items()
        if k.startswith("chart_") and v
    }

    return {
        "input": {
            "mode": raw.get("input_mode", "jira"),
            "csv_file": raw.get("input_csv_file", ""),
        },
        "jira": build_jira_config(db),
        "Workflow": workflow,
        "start_step": start_step,
        "issue_type": ["Total"] + issue_types,
        "chart_thresholds": chart_thresholds or None,
    }
