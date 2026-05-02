# ADR 0005: Configurable Cycle Time Start Step

**Status:** Accepted  
**Date:** 2026-05-02  
**Deciders:** Engineering Team

---

## Context and Problem Statement

Cycle time is calculated as the difference between the "done" step (last workflow step) and the step where active work begins. Previously, the code assumed `workflow[1]` (the second step) was always the start of active work. This is incorrect for teams that have multiple pre-work stages (e.g. `Backlog → Refined → In Progress → Done`) where `workflow[1]` is `Refined`, not `In Progress`.

## Decision

Introduce a `workflow_start_step` configuration key that allows users to designate which workflow step marks the beginning of active work. This value is stored in the `config` table and resolved at chart-render time.

### Resolution logic

1. If `workflow_start_step` is set and the value exists in the current workflow, use it.
2. Otherwise, fall back to `workflow[1]` (second step) for backwards compatibility.
3. If the workflow has fewer than 2 steps, fall back to the literal string `"In Progress"`.

### UI

A dropdown is shown in the Config page below the workflow builder (visible only when the workflow has ≥ 2 steps). It lists all steps except the last (done step). The selected value is saved alongside other config.

## Alternatives Considered

### Always use `workflow[1]`
- **Rejected**: Breaks for teams with multiple pre-work stages (e.g. `Backlog`, `Refined`).

### Let the user mark a step as "start" in the workflow builder
- **Considered**: More visual but significantly more complex to implement in the drag-and-drop list.

### Separate "start step" and "end step" selectors
- **Deferred**: End step is always `workflow[-1]` for now; this can be added in a future ADR if required.

## Consequences

### Positive
- Cycle time is now accurate for any workflow topology.
- Backwards compatible: existing deployments fall back to `workflow[1]` automatically.

### Negative / Trade-offs
- If the user rearranges the workflow after setting a start step and removes that step, the start step silently falls back to `workflow[1]`. A validation warning could be added in future.

## Implementation Notes

- `config_service.build_reader_config()` resolves `start_step` and injects it into the reader config dict alongside `"Workflow"`.
- `viewer.Backlog` reads `config["start_step"]` to set `self.in_progress_step`, used by `draw_timeline`, `draw_distribution`, `calculate_cycle_time`, and `get_kpis`.
- The `done_step` is always `workflow[-1]` and is not yet user-configurable.

## References

- `docs/diagrams/architecture.md`
- `backend/services/config_service.py` — `build_reader_config()`
- `backend/viewer/backlog.py` — `Backlog.__init__`
