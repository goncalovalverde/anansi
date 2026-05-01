# ADR 0003: Migrate Frontend from Vanilla JS to Vue 3 + Vite

**Status:** Accepted
**Date:** 2026-05-01
**Deciders:** Engineering Team

---

## Context and Problem Statement

The current vanilla JS frontend (~1,400 lines across 3 files) has growing maintenance friction:

- Manual DOM manipulation in `config.js` (chips, tags, workflow list) — re-renders require full `innerHTML` replacement and re-binding of all event listeners
- Tight coupling between `renderAllCharts` and the HTML structure it knows about
- Progress strip state is computed from scattered DOM queries rather than a single reactive source
- Two separate HTML pages make it impossible to share in-memory state (e.g. config loaded on dashboard page)
- No unit-testable units — all logic is entangled with `document.getElementById`

## Decision

Migrate to **Vue 3 (Composition API) + Vite** with **Vue Router 4** for SPA routing and **Pinia** for shared state.

Plotly.js remains loaded from CDN to avoid bundling 3 MB of chart library through Rollup.

### Why Vue 3, not React or Angular?

| Criterion | Vue 3 | React | Angular |
|---|---|---|---|
| Incremental adoption | ✅ Mounts onto any div | Partial | ❌ All-or-nothing |
| SFC readability (non-JS devs) | ✅ Template + script + style | ❌ JSX | Partial |
| Bundle size (gzipped) | ~34 KB | ~45 KB | ~130 KB |
| Plotly integration | `onMounted` → `Plotly.newPlot()` | Same but more boilerplate | Same |
| Team familiarity overhead | Low | Medium | High |

### New structure

```
frontend-vue/
  src/
    api/index.js             — same API calls, typed as plain functions
    stores/config.js         — Pinia: jira config, theme
    stores/data.js           — Pinia: dataset id, status, charts, kpis
    composables/useDataLoader.js — DataLoader lifecycle as composable
    views/DashboardView.vue  — replaces index.html + dashboard.js
    views/ConfigView.vue     — replaces config.html + config.js
    components/…             — AppHeader, KpiStrip, ChartCard, EmptyState, etc.
```

## Consequences

**Positive**
- Reactive state eliminates manual DOM sync
- Components are independently testable
- Single-page routing allows config → dashboard state sharing
- Vite HMR speeds up future development

**Negative / Risks**
- Node.js + npm required to build (new dev dependency)
- Plotly CDN dependency persists (acceptable trade-off)
- `frontend/` legacy directory kept in repo until migration is verified stable

## Related
- [ADR 0001](./0001-migrate-to-fastapi-sqlite.md) — FastAPI + SQLite architecture
- [ADR 0002](./0002-jira-discovery-api-endpoints.md) — Jira discovery endpoints
