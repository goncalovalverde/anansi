"""
Shared Backlog instance and response cache.

Both /api/charts and /api/flow build a Backlog from the same dataset and config.
This module caches at two levels:

1. **Request-scoped cache** (contextvars): Ultrafast (~0ns) in-request lookups.
   Automatically isolated per HTTP request. Useful if a single request accesses
   multiple expensive operations (e.g., multiple chart/kpi endpoints in sequence).

2. **Global cache** (thread-safe dict with TTL): Shared across requests.
   Per-key locking prevents thundering herd. Survives request boundaries.

This dual-layer design provides:
  - Request locality: First call in a request is slow (global cache lookup)
  - Subsequent calls in same request are instant (request-scope cache)
  - Cross-request reuse: Second request reuses the global cache (no rebuild)
  - Safety: Per-key locking + config-aware versioning

Cache lifetime (TTL_SECONDS) is long enough to make dataset navigation snappy
but short enough that a manual data reload is always reflected quickly.
Explicit invalidation is also called after every data load.
"""

import json
import logging
import sqlite3
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

TTL_SECONDS = 300  # 5 minutes

# Each cache entry: {"data": Any, "ts": float}
_cache: dict[str, dict] = {}

# One lock per cache key — created lazily.
_key_locks: dict[str, threading.Lock] = {}
_meta_lock = threading.Lock()  # guards _key_locks dict itself


def _get_lock(key: str) -> threading.Lock:
    """Return (creating if necessary) the per-key lock."""
    with _meta_lock:
        if key not in _key_locks:
            _key_locks[key] = threading.Lock()
        return _key_locks[key]


def _is_fresh(key: str) -> bool:
    entry = _cache.get(key)
    return entry is not None and time.monotonic() - entry["ts"] < TTL_SECONDS


def _config_signature(config: dict) -> str:
    return json.dumps(config, sort_keys=True, default=str)


def _evict_stale() -> None:
    """Remove expired entries. Called opportunistically on cache miss."""
    now = time.monotonic()
    stale = [k for k, v in list(_cache.items()) if now - v["ts"] >= TTL_SECONDS]
    for k in stale:
        _cache.pop(k, None)


# ------------------------------------------------------------------ #
#  Internal builders                                                   #
# ------------------------------------------------------------------ #


def _build_backlog(db: sqlite3.Connection, dataset_id: str, config: dict):
    from ..viewer.backlog import Backlog
    from . import data_service

    df = data_service.load_dataframe(db, dataset_id)
    return Backlog(df, config)


def _get_or_build(key: str, builder, request_cache=None) -> Any:
    """Double-checked locking with optional request-scoped cache fallback.

    1. If request_cache provided, check it first (ultrafast, ~0ns)
    2. Then check global cache (fast, ~1-10μs)
    3. If miss, acquire per-key lock and build
    4. Cache result in both request-scope and global cache
    """
    # Request-scoped cache is fastest (should be checked first)
    if request_cache is not None:
        result = request_cache.get(key)
        if result is not None:
            logger.debug("Request-scope cache hit for '%s'", key)
            return result

    # Global cache fast path — no lock needed
    if _is_fresh(key):
        cached_value = _cache[key]["data"]
        # Also cache in request scope for subsequent calls in this request
        if request_cache is not None:
            request_cache.set(key, cached_value)
        return cached_value

    lock = _get_lock(key)
    with lock:
        # Re-check inside lock (another thread may have built it while we waited)
        if _is_fresh(key):
            cached_value = _cache[key]["data"]
            # Also cache in request scope
            if request_cache is not None:
                request_cache.set(key, cached_value)
            return cached_value

        logger.debug("Cache miss for key '%s' — rebuilding", key)
        data = builder()
        _cache[key] = {"data": data, "ts": time.monotonic()}
        _evict_stale()

        # Also cache in request scope for subsequent calls in this request
        if request_cache is not None:
            request_cache.set(key, data)

        return data


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #


def get_backlog(db: sqlite3.Connection, dataset_id: str, request_cache=None):
    """Return a cached Backlog for this dataset, rebuilding if stale.

    Args:
        db: Database connection
        dataset_id: Dataset identifier
        request_cache: Optional RequestCache for request-scoped caching.
                      If provided, check it first before global cache.

    Returns:
        Backlog instance (from request-scope, global, or freshly built)
    """
    from . import config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    key = f"backlog:{dataset_id}:{sig}"
    return _get_or_build(key, lambda: _build_backlog(db, dataset_id, config), request_cache)


def get_dashboard_response(db: sqlite3.Connection, dataset_id: str, request_cache=None) -> dict:
    """Return cached {charts, kpis, callouts} for the dashboard endpoint.

    Args:
        db: Database connection
        dataset_id: Dataset identifier
        request_cache: Optional RequestCache for request-scoped caching

    Returns:
        Dict with keys: treemap, treemap_all, distribution, pbis_done, pbis_created,
                       story_points, type_issue, timeline_size, aging_heatmap,
                       epic_investment, kpis, callouts
    """
    from . import config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    dash_key = f"dashboard:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config), request_cache)
        response = backlog.get_all_charts()  # already parsed dicts
        response["kpis"] = backlog.get_kpis()
        response["callouts"] = backlog.get_callouts()
        return response

    return _get_or_build(dash_key, build, request_cache)


def get_flow_response(db: sqlite3.Connection, dataset_id: str, request_cache=None) -> dict:
    """Return cached flow charts + callouts for the flow endpoint.

    Args:
        db: Database connection
        dataset_id: Dataset identifier
        request_cache: Optional RequestCache for request-scoped caching

    Returns:
        Dict with flow charts and callouts
    """
    from . import config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    flow_key = f"flow:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config), request_cache)
        response = backlog.get_flow_charts()  # already parsed dicts
        response["callouts"] = backlog.get_flow_callouts()
        return response

    return _get_or_build(flow_key, build, request_cache)


def get_insights_response(db: sqlite3.Connection, dataset_id: str, request_cache=None) -> list:
    """Return cached insights for the insights endpoint.

    Args:
        db: Database connection
        dataset_id: Dataset identifier
        request_cache: Optional RequestCache for request-scoped caching

    Returns:
        List of insight dictionaries
    """
    from . import config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    insights_key = f"insights:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config), request_cache)
        return backlog.get_insights()

    return _get_or_build(insights_key, build, request_cache)


def get_trends_response(db: sqlite3.Connection, dataset_id: str, request_cache=None) -> dict:
    """Return cached trend charts for the trends endpoint.

    Args:
        db: Database connection
        dataset_id: Dataset identifier
        request_cache: Optional RequestCache for request-scoped caching

    Returns:
        Dict with trend charts
    """
    import json as json_mod

    import plotly.graph_objects as go

    from . import config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    trends_key = f"trends:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config), request_cache)
        methods = {
            "cumulative_flow": backlog.draw_cumulative_flow,
            "monthly_throughput": backlog.draw_monthly_throughput,
            "epic_progress": backlog.draw_epic_progress,
        }
        raw = {}
        for name, method in methods.items():
            try:
                raw[name] = method()
            except Exception as exc:
                logger.exception("Trend chart '%s' failed", name)
                raw[name] = go.Figure(layout={"title": f"{name} unavailable: {exc}"}).to_json()
        return {k: json_mod.loads(v) for k, v in raw.items()}

    return _get_or_build(trends_key, build, request_cache)


def invalidate(dataset_id: str) -> None:
    """Remove all cache entries for a dataset (call after data reload)."""
    keys = [k for k in list(_cache.keys()) if f":{dataset_id}:" in k]
    for k in keys:
        _cache.pop(k, None)
    logger.debug("Invalidated %d cache entries for dataset %s", len(keys), dataset_id)
