"""
Shared Backlog instance and response cache.

Both /api/charts and /api/flow build a Backlog from the same dataset and config.
This module caches:
  - The Backlog object (expensive DataFrame merge + cycle-time computation)
  - The full dashboard response (charts + kpis + callouts)
  - The full flow response (flow charts + callouts)

Per-key locking prevents the thundering-herd problem where concurrent requests
on a cold cache each trigger a full rebuild.

Cache lifetime (TTL_SECONDS) is long enough to make dataset navigation snappy
but short enough that a manual data reload is always reflected quickly.
Explicit invalidation is also called after every data load.
"""

import time
import threading
import logging
from typing import Any
import sqlite3

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
    return str(sorted(config.items()))


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
    import services.data_service as data_service
    from viewer.backlog import Backlog

    df = data_service.load_dataframe(db, dataset_id)
    return Backlog(df, config)


def _get_or_build(key: str, builder) -> Any:
    """Double-checked locking: return cached value or call builder once."""
    # Fast path — no lock needed
    if _is_fresh(key):
        return _cache[key]["data"]

    lock = _get_lock(key)
    with lock:
        # Re-check inside lock (another thread may have built it while we waited)
        if _is_fresh(key):
            return _cache[key]["data"]

        logger.debug("Cache miss for key '%s' — rebuilding", key)
        data = builder()
        _cache[key] = {"data": data, "ts": time.monotonic()}
        _evict_stale()
        return data


# ------------------------------------------------------------------ #
#  Public API                                                          #
# ------------------------------------------------------------------ #

def get_backlog(db: sqlite3.Connection, dataset_id: str):
    """Return a cached Backlog for this dataset, rebuilding if stale."""
    import services.config_service as config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    key = f"backlog:{dataset_id}:{sig}"
    return _get_or_build(key, lambda: _build_backlog(db, dataset_id, config))


def get_dashboard_response(db: sqlite3.Connection, dataset_id: str) -> dict:
    """Return cached {charts, kpis, callouts} for the dashboard endpoint."""
    import services.config_service as config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    dash_key = f"dashboard:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config))
        response = backlog.get_all_charts()   # already parsed dicts
        response["kpis"] = backlog.get_kpis()
        response["callouts"] = backlog.get_callouts()
        return response

    return _get_or_build(dash_key, build)


def get_flow_response(db: sqlite3.Connection, dataset_id: str) -> dict:
    """Return cached flow charts + callouts for the flow endpoint."""
    import services.config_service as config_service

    config = config_service.build_reader_config(db)
    sig = _config_signature(config)
    backlog_key = f"backlog:{dataset_id}:{sig}"
    flow_key = f"flow:{dataset_id}:{sig}"

    def build():
        backlog = _get_or_build(backlog_key, lambda: _build_backlog(db, dataset_id, config))
        response = backlog.get_flow_charts()   # already parsed dicts
        response["callouts"] = backlog.get_flow_callouts()
        return response

    return _get_or_build(flow_key, build)


def invalidate(dataset_id: str) -> None:
    """Remove all cache entries for a dataset (call after data reload)."""
    keys = [k for k in list(_cache.keys()) if f":{dataset_id}:" in k]
    for k in keys:
        _cache.pop(k, None)
    logger.debug("Invalidated %d cache entries for dataset %s", len(keys), dataset_id)
