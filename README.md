# anansi

<p align="center">
  <img src="docs/logo.png" alt="Anansi logo" width="260"/>
</p>

**Anansi** is a Jira/CSV backlog analytics dashboard that renders interactive Plotly charts in a browser UI.

## Architecture

Anansi runs as a **FastAPI** backend serving a **Vue 3 + Vite** frontend. Configuration and cached data are stored in a local **SQLite** database (`anansi.db`).

See `docs/adr/` for architectural decision records and `docs/diagrams/architecture.md` for Mermaid diagrams.

## Requirements

- Python 3.11+
- Node.js 18+ (required to build the frontend)

## Installation

```bash
pip install -r requirements.txt

# Build the frontend (required on first run and after any frontend changes)
cd frontend-vue && npm install && npm run build && cd ..
```

## Running

```bash
./start.sh
```

This installs Python dependencies, builds the frontend (first run only), and starts the backend. Alternatively, run manually:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

> **Rebuild the frontend** after any frontend changes: `cd frontend-vue && npm run build`

### Environment variables

| Variable         | Default      | Description                   |
|------------------|--------------|-------------------------------|
| `ANANSI_DB_PATH` | `anansi.db`  | Path to the SQLite database   |

## Usage

1. Navigate to **http://localhost:8000/#/config** and choose your data source:
   - **Jira**: enter your Jira URL, credentials, and JQL filter, then click **Test Connection**
   - **CSV**: drag and drop (or click to browse) a CSV file — it is processed in memory, nothing saved to disk
2. In the **Workflow** section, arrange your board columns and select the **Cycle Time Start Step** (the step that marks when active work begins).
3. Click **Save Configuration** then navigate to **http://localhost:8000** (Dashboard).
4. Click **Load Data** — a progress bar shows issues fetched / total while Jira data loads.
5. Once ready, all 8 charts are rendered on the dashboard.

## Project structure

```
anansi/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── database.py             # SQLite init & connection factory
│   ├── api/
│   │   ├── config.py           # /api/config routes
│   │   ├── data.py             # /api/data routes
│   │   └── charts.py           # /api/charts routes
│   ├── services/
│   │   ├── config_service.py   # Config CRUD + secret masking
│   │   └── data_service.py     # Dataset lifecycle + background load
│   ├── reader/
│   │   ├── __init__.py         # Dispatcher (jira / csv)
│   │   ├── jira.py             # Jira pagination & field extraction
│   │   ├── csv.py              # CSV reader
│   │   └── cache.py            # SQLite-backed cache (replaces pickle)
│   └── viewer/
│       └── backlog.py          # Plotly chart builder (returns JSON)
├── frontend-vue/               # Vue 3 + Vite frontend
│   ├── src/
│   │   ├── main.js             # App entry point
│   │   ├── App.vue             # Root component + global notification
│   │   ├── router/index.js     # Vue Router (hash history)
│   │   ├── api/index.js        # Fetch wrapper
│   │   ├── stores/
│   │   │   ├── config.js       # Pinia: theme
│   │   │   └── data.js         # Pinia: dataset, charts, kpis, status
│   │   ├── composables/
│   │   │   └── useDataLoader.js # Poll/restore lifecycle
│   │   ├── views/
│   │   │   ├── DashboardView.vue
│   │   │   └── ConfigView.vue
│   │   ├── components/         # AppHeader, KpiStrip, ChartCard, …
│   │   └── assets/styles.css
│   ├── dist/                   # Built output served by FastAPI
│   └── vite.config.js
├── docs/
│   ├── adr/
│   │   ├── 0001-migrate-to-fastapi-sqlite.md
│   │   ├── 0002-jira-discovery-api-endpoints.md
│   │   └── 0003-vue3-vite-frontend.md
│   └── diagrams/
│       └── architecture.md
└── requirements.txt
```

## API reference

| Method   | Path                          | Description                              |
|----------|-------------------------------|------------------------------------------|
| GET      | `/api/config`                 | Get current config (secrets masked)      |
| PUT      | `/api/config`                 | Update config keys                       |
| GET      | `/api/config/workflow`        | Get workflow steps                       |
| PUT      | `/api/config/workflow`        | Set workflow steps                       |
| GET      | `/api/config/issue-types`     | Get issue types                          |
| PUT      | `/api/config/issue-types`     | Set issue types                          |
| POST     | `/api/config/test-connection` | Test Jira connectivity                   |
| POST     | `/api/data/load`              | Start Jira data load (background task)   |
| POST     | `/api/data/upload-csv`        | Upload and process a CSV file in memory  |
| GET      | `/api/data/{id}/status`       | Poll dataset status + progress           |
| DELETE   | `/api/data/cache`             | Delete all cached datasets               |
| GET      | `/api/charts/{dataset_id}`    | Get all 8 charts as Plotly JSON          |