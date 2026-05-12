# ADR 0007: Architecture Deepening — Five Structural Refactors

**Status:** Accepted  
**Date:** 2026-05-13  
**Deciders:** Engineering Team

---

## Context and Problem Statement

The Anansi backend evolved organically and accumulated several shallow-module patterns:

1. **Duplicate dataset persistence** — `reader/cache.py` duplicated logic already in `services/data_service.py`, splitting caching responsibility across two layers.
2. **Monolithic Backlog class** — `viewer/backlog.py` (~503 lines) mixed chart generation, insight computation, and callout logic in one file.
3. **Scattered field-detection heuristics** — Jira field detection (story points, epic link) was inlined in the API route handler, unreachable by other callers.
4. **Inconsistent cache routing** — some API endpoints instantiated `Backlog` directly; others went through `backlog_cache`. This split made it impossible to guarantee cache consistency.
5. **Non-configurable chart thresholds** — `ChartConfig` used class-level constants, requiring code changes to adjust sensitivity.

Each problem violated the *depth* principle: interfaces were nearly as complex as their implementations, offering little leverage to callers.

## Decision

Apply five targeted refactors that deepen existing modules without adding new abstractions:

### 1. Consolidate dataset persistence

- Delete `reader/cache.py`.
- Strip internal cache logic from `reader/jira.py` — it becomes a pure data fetcher.
- All persistence lives in `services/data_service.py` and `services/backlog_cache.py`.

### 2. Extract BacklogInsightsMixin

- Move `get_insights()`, `get_callouts()`, and `get_flow_callouts()` into `viewer/backlog_insights.py` as a mixin.
- `Backlog` inherits `BacklogInsightsMixin` (MRO: insights → charts → flow → trends).
- Reduces `backlog.py` from ~503 to ~270 lines.

### 3. Centralize field detection in config_service

- Add `detect_story_point_fields()` and `detect_epic_link_fields()` to `services/config_service.py`.
- API route handler (`api/config.py`) delegates to these functions.

### 4. Uniform cache routing

- Add `get_insights_response()` and `get_trends_response()` to `services/backlog_cache.py`.
- `api/insights.py` and `api/trends.py` become thin pass-throughs.
- Fix `_config_signature` to use `json.dumps(sort_keys=True)` for deterministic hashing of nested dicts.

### 5. Configurable ChartConfig

- Convert `ChartConfig` from class-level constants to an instantiable class.
- Tunable thresholds are instance attributes initialized from `_THRESHOLD_DEFAULTS` dict.
- Style/layout constants (colors, heights) remain class-level — never overridable.
- `Backlog.__init__` creates `self.chart_config = ChartConfig(config.get("chart_thresholds"))`.
- New API endpoints: `GET/PUT /api/config/chart-thresholds`.

## Consequences

### Positive

- **Locality**: Cache logic concentrated in one service; insight logic in one mixin; field detection in one function.
- **Leverage**: Callers of `backlog_cache` get full caching + locking for free. Callers of `ChartConfig(overrides)` get all defaults merged with zero knowledge of which keys exist.
- **Testability**: `Backlog` mixins can be tested independently; `jira.py` is trivially mockable as a pure fetcher.
- **Configurability**: Chart thresholds adjustable per-deployment without code changes.

### Negative / Trade-offs

- MRO complexity: `Backlog` now has 4 mixins. Method resolution order matters if mixins ever share method names.
- `_THRESHOLD_DEFAULTS` is duplicated as both a dict and as attribute assignments in `__init__` — kept for backward compatibility with `self.chart_config.WIP_HIGH_THRESHOLD` access pattern.

## References

- `backend/viewer/backlog_insights.py` — extracted mixin
- `backend/viewer/chart_config.py` — `_THRESHOLD_DEFAULTS` + instantiable `ChartConfig`
- `backend/services/backlog_cache.py` — unified cache with config signature fix
- `backend/services/config_service.py` — `detect_*_fields()`, `get_chart_thresholds()`, `set_chart_thresholds()`
- `docs/diagrams/architecture.md` — updated component + class diagrams
