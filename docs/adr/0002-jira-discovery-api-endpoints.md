# ADR 0002: Jira Discovery API Endpoints

**Status:** Accepted  
**Date:** 2026-05-01  
**Deciders:** Engineering Team

---

## Context and Problem Statement

Configuring Anansi requires users to manually look up two pieces of Jira metadata:

1. **Project key** — needed to write a JQL filter (`project = MYPROJECT`). Previously the user had to copy this from the Jira URL or admin panel.
2. **Custom field IDs** for Story Points (`customfield_XXXXX`) and Epic Link — only discoverable through Jira's admin screens, invisible to most product owners.

This created friction at setup time and was a common source of misconfiguration (wrong field ID → no story points data on the dashboard).

---

## Decision

Add two new `POST` endpoints to the FastAPI config router that call the already-authenticated Jira connection to discover metadata on demand:

| Endpoint | Returns |
|---|---|
| `POST /api/config/jira-projects` | List of `{key, name}` for all projects accessible with the stored credentials |
| `POST /api/config/jira-fields`   | Lists of candidate `{id, name}` objects for story-points fields and epic-link fields, filtered by name keywords |

Both endpoints accept an optional request body of config overrides (same format as `test-connection`), allowing the frontend to pass unsaved form values before a permanent save.

### Why POST not GET?

Credentials are never sent in query parameters or headers from the form — they are transmitted as a JSON body, matching the pattern already established by `test-connection` and `jira-statuses`. Both endpoints are functionally read-only against Jira but require a body for credential passing.

### Field detection heuristic

Story-points candidates: any `customfield_*` whose name contains `story point`, `story_point`, `points`, or `sp` (case-insensitive).  
Epic-link candidates: any `customfield_*` whose name contains `epic link`, `epic_link`, `epic name`, or `parent epic`.

The frontend pre-fills the first match but leaves the field editable so the user can override.

---

## Consequences

**Positive**
- Product owners can complete setup without needing Jira admin access or API knowledge.
- The project picker builds the JQL automatically, reducing misconfiguration.
- Auto-detect eliminates the most common support request (wrong story-points field ID).

**Negative / Risks**
- Two additional live Jira API calls are made during config page load (one per button click — not automatic).
- Field detection is heuristic: non-standard field names will not be auto-detected and still require manual entry.
- `jira_instance.projects()` returns all accessible projects; large Jira installations with many projects may have a slow response on first call.

---

## Alternatives Considered

| Option | Reason rejected |
|---|---|
| Static lookup table of common field IDs | Varies per Jira installation; would give false confidence |
| GET endpoints with credentials in headers | Inconsistent with existing auth pattern; credentials should not appear in headers or URL |
| Fetch fields on page load automatically | Would add latency on every config page open; better to trigger on demand |

---

## Related

- [ADR 0001](./0001-migrate-to-fastapi-sqlite.md) — FastAPI + SQLite migration (establishes the API architecture this builds on)
- Component diagram: [`/docs/diagrams/`](../diagrams/)
