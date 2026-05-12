import sqlite3
import os
from pathlib import Path

DB_PATH = os.environ.get("ANANSI_DB_PATH", "anansi.db")

SECRET_KEYS = {"jira_password", "jira_oauth_token", "jira_oauth_token_secret", "jira_pat_token"}

_DEFAULT_CONFIG = [
    ("jira_url", ""),
    ("jira_jql_query", ""),
    ("jira_auth_method", "basic"),
    ("jira_username", ""),
    ("jira_password", ""),
    ("jira_story_points_field", "customfield_10016"),
    ("jira_epic_link_field", "customfield_10014"),
    ("workflow_start_step", ""),
    ("jira_oauth_token", ""),
    ("jira_oauth_token_secret", ""),
    ("jira_oauth_consumer_key", ""),
    ("jira_oauth_key_cert_file", ""),
    ("jira_pat_token", ""),
    ("jira_api_version", "2"),
    ("input_mode", "jira"),
    ("input_csv_file", ""),
]

_DEFAULT_WORKFLOW = ["Backlog", "In Progress", "Done"]
_DEFAULT_ISSUE_TYPES = ["Story", "Bug", "Task", "Epic"]


def get_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    conn = get_db(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS workflow_steps (
                position INTEGER PRIMARY KEY,
                step     TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS issue_types (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id               TEXT PRIMARY KEY,
                config_hash      TEXT NOT NULL,
                source           TEXT NOT NULL,
                status           TEXT DEFAULT 'pending',
                error            TEXT,
                progress_loaded  INTEGER DEFAULT 0,
                progress_total   INTEGER DEFAULT 0,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dataset_rows (
                dataset_id TEXT    NOT NULL,
                row_index  INTEGER NOT NULL,
                row_data   TEXT    NOT NULL,
                PRIMARY KEY (dataset_id, row_index),
                FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
            );
            """
        )

        row_count = conn.execute("SELECT COUNT(*) FROM config").fetchone()[0]
        if row_count == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                _DEFAULT_CONFIG,
            )
        else:
            # Seed any new default config keys into existing databases
            conn.executemany(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                _DEFAULT_CONFIG,
            )

        # Migrate existing datasets table: add progress columns if missing
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(datasets)")}
        for col, definition in [
            ("progress_loaded", "INTEGER DEFAULT 0"),
            ("progress_total",  "INTEGER DEFAULT 0"),
        ]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE datasets ADD COLUMN {col} {definition}")

        wf_count = conn.execute("SELECT COUNT(*) FROM workflow_steps").fetchone()[0]
        if wf_count == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO workflow_steps (position, step) VALUES (?, ?)",
                enumerate(_DEFAULT_WORKFLOW),
            )

        it_count = conn.execute("SELECT COUNT(*) FROM issue_types").fetchone()[0]
        if it_count == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO issue_types (name) VALUES (?)",
                [(t,) for t in _DEFAULT_ISSUE_TYPES],
            )

    conn.close()
