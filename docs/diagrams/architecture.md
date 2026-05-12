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
        ConfigAPI["/api/config\n+ /chart-thresholds"]
        DataAPI["/api/data"]
    end

    FastAPI --> ChartsAPI
    FastAPI --> FlowAPI
    FastAPI --> TrendsAPI
    FastAPI --> InsightsAPI
    FastAPI --> ConfigAPI
    FastAPI --> DataAPI

    ChartsAPI   --> BacklogCache["services.BacklogCache\nget_backlog · get_insights_response\nget_trends_response\n(double-checked locking)"]
    FlowAPI     --> BacklogCache
    TrendsAPI   --> BacklogCache
    InsightsAPI --> BacklogCache

    BacklogCache --> BacklogViewer["viewer.Backlog\n↳ BacklogInsightsMixin\n↳ BacklogChartsMixin\n↳ FlowChartsMixin\n↳ TrendChartsMixin"]

    ConfigAPI --> ConfigSvc["ConfigService\ndetect_story_point_fields\ndetect_epic_link_fields\nget/set_chart_thresholds"]
    DataAPI   --> DataSvc[DataService]

    ConfigSvc --> SQLite[("SQLite anansi.db")]
    DataSvc   --> SQLite
    DataSvc   --> JiraReader["reader.Jira\n(pure data fetcher)"]
    DataSvc   --> CSVReader["reader.CSV (in-memory)"]
    JiraReader --> JiraAPI["Jira Cloud API"]

    BacklogViewer --> ChartConfigInst["ChartConfig(overrides)\ntunable thresholds"]
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
    API->>API: BacklogCache.get_backlog(dataset_id)
    API->>DB: SELECT dataset_rows
    API-->>B: {treemap, distribution, pbis_done, ...kpis, callouts}
    B->>API: GET /api/insights/{dataset_id}
    API->>API: BacklogCache.get_insights_response(dataset_id)
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

## 7. Backlog Module — Internal Component Structure

```mermaid
classDiagram
    class BacklogData {
        <<viewer/backlog_data.py>>
        +treemap_data: DataFrame
        +done_df: DataFrame
        +active_df: DataFrame
        +ct_df: DataFrame
        +from_cycle_data(treemap_data, done_step) BacklogData
        +build_weekly_counts(dates, fill_zeros) Series
        +build_event_wip(in_prog_dates, done_dates) Series
        +build_cumulative_series(dates, week_range) Series
    }

    class BacklogInsightsMixin {
        <<viewer/backlog_insights.py>>
        +get_insights() list
        +get_callouts() list
        +get_flow_callouts() list
    }

    class BacklogChartsMixin {
        <<viewer/backlog_charts.py>>
        +draw_treemap() str
        +draw_treemap_all() str
        +draw_distribution() str
        +draw_issues_histogram(date_column) str
        +draw_story_points() str
        +draw_type_issue() str
        +draw_timeline_size() str
        +draw_aging_heatmap() str
        +draw_epic_investment() str
    }

    class FlowChartsMixin {
        <<viewer/flow_charts.py>>
        +draw_flow_efficiency() str
        +draw_wip_trend() str
        +draw_throughput() str
        +draw_throughput_histogram() str
    }

    class TrendChartsMixin {
        <<viewer/trend_charts.py>>
        +draw_cumulative_flow() str
        +draw_monthly_throughput() str
        +draw_epic_progress() str
    }

    class Backlog {
        <<viewer/backlog.py>>
        +done_step: str
        +in_progress_step: str
        +treemap_data: DataFrame
        +data: BacklogData
        +chart_config: ChartConfig
        -_done_df: DataFrame
        -_active_df: DataFrame
        -_ct_df: DataFrame
        +get_all_charts() dict
        +get_flow_charts() dict
        +get_kpis() dict
        -_normalize_status(status) str
        -_resolve_step(df, preferred, workflow, reversed_order) str
    }

    class ChartConfig {
        <<viewer/chart_config.py — instantiable>>
        +HEATMAP_MIN_HEIGHT$
        +NORMAL_WEEK_COLOR$
        +WIP_HIGH_THRESHOLD: int
        +CYCLE_TIME_HIGH_DAYS: int
        +FLOW_EFFICIENCY_GOOD_PCT: int
        +__init__(overrides: dict|None)
    }

    class EpicColorMap {
        <<viewer/chart_config.py — singleton>>
        -_color_map: dict
        -_lock: Lock
        +get_color(epic_name) str
        +clear()
    }

    class BacklogCache {
        <<services/backlog_cache.py>>
        +get_backlog(dataset_id, db) Backlog
        +get_insights_response(dataset_id, db) list
        +get_trends_response(dataset_id, db) dict
        -_config_signature(db) str
    }

    class create_empty_state_figure {
        <<viewer/chart_helpers.py>>
        +create_empty_state_figure(message, height) str
    }

    Backlog --|> BacklogInsightsMixin : inherits
    Backlog --|> BacklogChartsMixin : inherits
    Backlog --|> FlowChartsMixin : inherits
    Backlog --|> TrendChartsMixin : inherits
    Backlog --> BacklogData : creates via from_cycle_data()
    Backlog --> ChartConfig : creates instance in __init__
    BacklogData --* Backlog : stored as .data
    BacklogInsightsMixin --> ChartConfig : reads self.chart_config
    BacklogChartsMixin --> ChartConfig : reads self.chart_config
    BacklogChartsMixin --> EpicColorMap : uses for colors
    BacklogChartsMixin --> create_empty_state_figure : uses for empty states
    FlowChartsMixin --> BacklogData : calls build_event_wip / build_weekly_counts
    FlowChartsMixin --> ChartConfig : reads self.chart_config
    TrendChartsMixin --> BacklogData : calls build_cumulative_series
    BacklogCache --> Backlog : instantiates and caches
```


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
        DashboardView --> ChartCard_dash["ChartCard x11\ntreemap · pbis_created · type_issue\npbis_done · story_points · timeline\ndistribution · timeline_size\naging_heatmap · epic_investment\nthroughput_histogram"]
    end

    subgraph flow ["FlowView (/flow)"]
        FlowView --> ChartCard6["ChartCard x6\nflow_efficiency · wip_trend · throughput\ntimeline · distribution · timeline_size"]
    end

    subgraph trends ["TrendsView (/trends)"]
        TrendsView --> ChartCard3["ChartCard x3\ncumulative_flow · monthly_throughput · epic_progress"]
    end

    DashboardView --> ChartCard_dash
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
