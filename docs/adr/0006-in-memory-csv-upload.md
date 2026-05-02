# ADR 0006: In-Memory CSV Upload via Multipart Endpoint

**Status:** Accepted  
**Date:** 2026-05-02  
**Deciders:** Engineering Team

---

## Context and Problem Statement

Previously, CSV-mode required users to enter an absolute file path to a CSV file on the server's filesystem (`input_csv_file` config key). This is a poor UX for a local web tool — it requires manual path lookup, fails on Windows path separators, and gives no feedback if the path is wrong until data load is triggered.

## Decision

Replace the path-text-input with a **drag-and-drop / file-picker upload** UI. The file is sent as a multipart `POST /api/data/upload-csv` request, decoded and parsed entirely in memory using `io.StringIO`, and stored directly into the `dataset_rows` table. No file is written to disk.

### Endpoint contract

```
POST /api/data/upload-csv
Content-Type: multipart/form-data

file: <.csv file>

→ 200 { dataset_id: string, cached: bool }
→ 400 if not a .csv file
→ 422 if CSV cannot be parsed
```

The dataset is content-hashed (MD5 of raw bytes) so re-uploading the same file reuses the cached dataset.

### Processing flow

1. Decode bytes as UTF-8 (with BOM stripping via `utf-8-sig`)
2. Parse with `pd.read_csv(io.StringIO(text))`
3. Apply workflow datetime column parsing (same as file-path mode)
4. Insert rows into `dataset_rows`, mark dataset `ready` immediately
5. Return `dataset_id`

The frontend stores `dataset_id` in `localStorage` so the dashboard can pick it up without a separate "Load Data" click.

## Alternatives Considered

### Keep the file path input
- **Rejected**: Requires the user to know the server's filesystem layout. Brittle; no feedback until load time.

### Save uploaded file to `backend/uploads/`
- **Rejected**: Introduces disk state management (cleanup, naming, permissions). In-memory processing is sufficient for typical CSV sizes and simpler to reason about.

### Stream the file through pandas directly
- **Considered**: FastAPI's `UploadFile` supports `read()` and `read(chunk)`. For CSV parsing pandas needs the full content, so full `await file.read()` is the correct approach.

## Consequences

### Positive
- Zero-friction CSV onboarding: drag, drop, done.
- No server-side disk writes or cleanup needed.
- Content-hashed deduplication: identical files reuse cached datasets.
- UTF-8 BOM handling covers Excel-exported CSVs.

### Negative / Trade-offs
- Very large CSV files are read fully into memory in the FastAPI worker. For typical backlog exports (< 10 MB) this is negligible.
- The `input_csv_file` config key is retained for backwards compatibility with existing configs but is no longer used by the upload flow.

## Implementation Notes

- `reader/csv.py` exposes two functions: `read(path, workflow)` (file-path mode, kept for CLI compatibility) and `read_from_string(text, workflow)` (in-memory, used by the upload endpoint).
- `python-multipart` was already a project dependency (required by FastAPI for any file upload).
- The frontend upload component (`ConfigView.vue`) shows drag-over, uploading, and success states. Errors are shown inline.

## References

- `docs/diagrams/architecture.md` — Sequence Diagram 4 (CSV Upload Flow)
- `backend/api/data.py` — `upload_csv` endpoint
- `backend/reader/csv.py` — `read_from_string`
- `frontend-vue/src/views/ConfigView.vue` — CSV upload UI
