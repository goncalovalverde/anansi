# Anansi Architecture Diagrams

## 1. Architecture (C4 Component)

```mermaid
graph TD
    Browser["Browser\nVue 3 SPA"] -->|REST| FastAPI["FastAPI backend"]

    subgraph api ["API Routes"]
        ChartsAPI["/api/charts\ntreemap · timeline · kpis · callouts"]
        FlowAPI["/api/flow\nefficiency · wip_trend · throughput"]
        TrendsAPI["/api/trends\ncumulative_flow · monthly · epic_progress"]
        InsightsAPI["/api/insights\nalert / warn / ok pills"]
        ConfigAPI["/api/config"]
        DataAPI["/api/data"]
    end

    FastAPI --> ChartsAPI
    FastAPI --> FlowAPI
    FastAPI --> TrendsAPI
    FastAPI --> InsightsAPI
    FastAPI --> ConfigAPI
    FastAPI --> DataAPI

    ChartsAPI  --> BacklogViewer["viewer.Backlog\nget_all_charts · get_kpis\nget_callouts · get_insights\ndraw_flow_* · draw_trend_*"]
    FlowAPI    --> BacklogViewer
    TrendsAPI  --> BacklogViewer
    InsightsAPI --> BacklogViewer

    ConfigAPI --> ConfigSvc[ConfigService]
    DataAPI   --> DataSvc[DataService]

    ConfigSvc --> SQLite[("SQLite anansi.db")]
    DataSvc   --> SQLite
    DataSvc   --> JiraReader["reader.Jira"]
    DataSvc   --> CSVReader["reader.CSV (in-memory)"]
    JiraReader --> JiraAPI["Jira Cloud API"]
    JiraReader --> SQLiteCache["SQLite cache\ndataset_rows table"]

    BacklogViewer -->|"Plotly JSON\n+ callouts + insights"| FastAPI
```

## 2. SQLite Schema ERD

```mermaid
erDiagram
    config {
        text key PK
        text value
    }
    workflow_steps {
        int position PK
        text step
    }
    issue_types {
        int id PK
        text name
    }
    datasets {
        text id PK
        text config_hash
        text source
        text status
        text error
        int progress_loaded
        int progress_total
        timestamp created_at
    }
    dataset_rows {
        text dataset_id FK
        int row_index
        text row_data
    }
    datasets ||--o{ dataset_rows : "has"
```

## 3. Sequence Diagram — Jira Data Load Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant API as FastAPI
    participant DB as SQLite
    participant JR as Jira API

    B->>API: POST /api/data/load
    API->>DB: check existing dataset by config_hash
    alt cache hit
        DB-->>API: dataset_id (status=ready)
        API-->>B: {dataset_id, cached: true}
    else no cache
        API->>DB: INSERT datasets (status=pending)
        API-->>B: {dataset_id, cached: false}
        API-)API: BackgroundTask: load_data_task
        loop poll every 2s
            B->>API: GET /api/data/{id}/status
            API-->>B: {status: loading, progress_loaded: N, progress_total: M}
            note over B: progress bar shows N/M
        end
        loop per 100-issue chunk
            API->>JR: search_issues(jql, expand=changelog)
            JR-->>API: chunk (100 issues, total=M)
            API->>DB: UPDATE datasets progress_loaded, progress_total
        end
        API->>DB: INSERT dataset_rows (JSON)
        API->>DB: UPDATE datasets status=ready
        B->>API: GET /api/data/{id}/status
        API-->>B: {status: ready}
    end
    B->>API: GET /api/charts/{dataset_id}
    API->>DB: SELECT dataset_rows
    API-->>B: {treemap, distribution, pbis_done, ...kpis, callouts}
    B->>API: GET /api/insights/{dataset_id}
    API-->>B: [{type, message}, ...]
    B->>B: Plotly.newPlot() x8
    B->>B: InsightBar renders alert/warn/ok pills
    B->>B: ChartCard callout strips rendered per chart
```

## 4. Sequence Diagram — CSV Upload Flow

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant API as FastAPI

    U->>B: Select .csv file (drag & drop or file picker)
    B->>API: POST /api/data/upload-csv (multipart)
    API->>API: decode UTF-8, pd.read_csv(StringIO)
    API->>API: apply workflow datetime parsing
    API->>API: MD5 content hash → check cache
    alt identical file already loaded
        API-->>B: {dataset_id, cached: true}
    else new file
        API->>API: INSERT dataset + rows, status=ready
        API-->>B: {dataset_id, cached: false}
    end
    B->>B: persist dataset_id to localStorage
    B-->>U: ✅ filename — "Ready, go to Dashboard"
```

## 5. Vue Component Hierarchy

```mermaid
graph TD
    App --> AppSidebar
    App --> AppTopBar
    App --> RouterView

    RouterView --> DashboardView
    RouterView --> FlowView
    RouterView --> TrendsView
    RouterView --> ConfigView

    subgraph dashboard ["DashboardView (/)"]
        DashboardView --> KpiStrip
        DashboardView --> InsightBar
        DashboardView --> ChartCard8["ChartCard x8\ntreemap · pbis_created · type_issue\npbis_done · story_points\ntimeline · distribution · timeline_size"]
    end

    subgraph flow ["FlowView (/flow)"]
        FlowView --> ChartCard6["ChartCard x6\nflow_efficiency · wip_trend · throughput\ntimeline · distribution · timeline_size"]
    end

    subgraph trends ["TrendsView (/trends)"]
        TrendsView --> ChartCard3["ChartCard x3\ncumulative_flow · monthly_throughput · epic_progress"]
    end

    DashboardView --> ChartCard8
    FlowView      --> ChartCard6
    TrendsView    --> ChartCard3

    AppSidebar --> routeLink["router-link\n(Dashboard · Flow · Trends · Config)"]
```

## 6. Sequence Diagram — Flow / Trends Chart Load

```mermaid
sequenceDiagram
    participant B as Browser
    participant API as FastAPI
    participant DB as SQLite

    Note over B: User clicks Flow or Trends in sidebar
    B->>B: Vue Router navigates to /flow or /trends
    B->>B: FlowView / TrendsView onMounted
    alt store.flowCharts already set
        B->>B: re-render from store (no network call)
    else no cached flow charts
        B->>API: GET /api/flow/{dataset_id}
        API->>DB: SELECT dataset_rows
        API->>API: Backlog.draw_flow_efficiency / draw_wip_trend / draw_throughput
        API-->>B: {flow_efficiency, wip_trend, throughput, timeline, distribution, timeline_size}
        B->>B: store.setFlowCharts(data)
        B->>B: Plotly.newPlot() x6
    end
```
