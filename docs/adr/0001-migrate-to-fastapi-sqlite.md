# ADR 0001: Migrate Anansi from CLI to FastAPI + SQLite Web Application

**Status:** Accepted  
**Date:** 2025-01-01  
**Deciders:** Engineering Team

---

## Context and Problem Statement

Anansi currently operates as a CLI Python script (`anansi.py`) that:
- Reads configuration from a flat `config.yml` file on disk
- Fetches data from Jira or a CSV file
- Caches results as pickle files in `/tmp`
- Renders charts using Plotly's `.show()` method, opening multiple browser tabs sequentially

This approach has several limitations:
- **Single-user, single-machine**: No web access; must be run from a terminal
- **No persistent configuration**: `config.yml` must be edited manually
- **Security risk**: Pickle cache in `/tmp` is susceptible to RCE if tampered with
- **Poor UX**: Charts open as separate browser tabs in sequence; no dashboard view
- **No concurrent safety**: File-based cache has no locking or consistency guarantees
- **Dependency bloat**: `dash`, `pandasgui`, `dash_bootstrap_components` unused or under-utilized

## Decision

Migrate Anansi to a **FastAPI backend + Vanilla JS frontend** architecture backed by **SQLite** for both configuration persistence and data caching.

### Architecture Summary

| Layer | Technology | Rationale |
|---|---|---|
| Backend API | FastAPI (Python) | Async-capable, fast, typed, auto-docs via OpenAPI |
| Database | SQLite (stdlib `sqlite3`) | Zero-dependency, single-file, sufficient for single-user |
| Frontend | Vanilla JS + Plotly.js | No build toolchain; CDN-served Plotly; minimal complexity |
| Cache | SQLite `dataset_rows` table | Replaces pickle; structured, safe, concurrent-read via WAL |

## Alternatives Considered

### Flask instead of FastAPI
- **Rejected**: Flask lacks async support, has no built-in data validation, and requires more boilerplate for OpenAPI documentation. FastAPI's `BackgroundTasks` integrates cleanly with the background data-loading pattern needed.

### Django instead of FastAPI
- **Rejected**: Django's ORM, migrations, and admin overhead is disproportionate for a single-user tool. Django's request/response cycle is less suited to background task patterns without Celery.

### React / Vue / Svelte frontend
- **Rejected**: Introduces a build toolchain (Node.js, bundler, transpiler) that complicates deployment. Vanilla JS with ES modules is sufficient for the dashboard and configuration pages. Plotly.js provides the rendering layer.

### PostgreSQL instead of SQLite
- **Rejected**: Anansi is a single-user local tool. PostgreSQL requires a running server process, separate installation, and connection management. SQLite in WAL mode provides sufficient concurrency for one user with a background worker thread.

### File-based cache (keep pickle)
- **Rejected**: Pickle deserialization of untrusted data is a known Python RCE vector. Storing cache in SQLite as JSON-serialised rows is safe, structured, and queryable. Storing in the same database as configuration also simplifies deployment (one file).

### JSON file for configuration
- **Considered but rejected**: A JSON config file still requires manual editing, has no masking for secrets, and does not support atomic updates. SQLite provides ACID transactions and allows the frontend to read/write config safely.

## Consequences

### Positive
- **Web-first UX**: All 8 charts rendered on a single dashboard page; no multiple browser tabs
- **Persistent, editable config**: Configuration stored in SQLite, editable via browser UI with secret masking
- **No more pickle RCE risk**: Cache stored as structured JSON in SQLite `dataset_rows`
- **Concurrent-safe reads**: SQLite WAL journal mode allows the background data-loading thread and the API request handler to read simultaneously without blocking
- **Stateless chart rendering**: Charts are rendered by dataset_id; the same dataset can be visualized multiple times without re-fetching from Jira
- **Clear cache via API**: `DELETE /api/data/cache` replaces manual `/tmp` file deletion
- **No config.yml on disk**: Secrets are stored only in SQLite (not in version-controlled YAML)

### Negative / Trade-offs
- **Added runtime dependencies**: `fastapi`, `uvicorn[standard]`, `python-multipart`
- **Local server required**: Users must run `uvicorn backend.main:app` instead of `python anansi.py`
- **SQLite file must be writable**: The `anansi.db` file in the project root must be writable by the process
- **Background thread isolation**: `load_data_task` must open its own SQLite connection; this is an intentional constraint documented in `data_service.py`

## Implementation Notes

- `SECRET_KEYS = {"jira_password", "jira_oauth_token", "jira_oauth_token_secret"}` are masked with `"***"` in all API responses
- `GET /api/config` never returns actual secret values; `PUT /api/config` ignores `""` and `"***"` to avoid overwriting stored secrets with empty updates
- Config hash (MD5 of sorted config values + workflow steps) invalidates the cache whenever any setting changes
- The "Total" issue_type is injected at data-service load time, not persisted in `issue_types` table

## References

- `docs/diagrams/architecture.md` — Mermaid diagrams for current and target architectures
- FastAPI documentation: https://fastapi.tiangolo.com
- SQLite WAL mode: https://www.sqlite.org/wal.html
