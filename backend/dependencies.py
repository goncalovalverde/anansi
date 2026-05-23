"""FastAPI dependencies for Anansi backend."""

import contextvars
import sqlite3
from typing import Any, Callable, Generator, Optional

from . import database

# Request-scoped cache — automatically isolated per HTTP request
class RequestCache:
    """Request-scoped cache for expensive objects during a single HTTP request.

    Automatically isolated per request via contextvars. Useful to avoid redundant
    recomputation if a single request accesses multiple expensive operations
    (e.g., multiple chart methods on the same dataset).

    Example:
        cache = get_request_cache()
        backlog = cache.get_or_build("backlog_123", lambda: expensive_build())
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if not found."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Store a value in the request-scoped cache."""
        self._cache[key] = value

    def get_or_build(self, key: str, builder: Callable[[], Any]) -> Any:
        """Return cached value or call builder() and cache the result."""
        if key not in self._cache:
            self._cache[key] = builder()
        return self._cache[key]

    def clear(self) -> None:
        """Clear all cached entries (useful for testing)."""
        self._cache.clear()


_request_cache_var: contextvars.ContextVar[Optional["RequestCache"]] = contextvars.ContextVar(
    "request_cache", default=None
)


def get_request_cache() -> RequestCache:
    """FastAPI dependency to get request-scoped cache.

    Automatically creates a new cache for each HTTP request and stores it
    in a contextvars ContextVar so it's isolated per request/thread.

    Example usage in an endpoint:
        from fastapi import Depends

        @router.get("/charts/{dataset_id}")
        def get_charts(dataset_id: str,
                       cache: RequestCache = Depends(get_request_cache)):
            backlog = cache.get_or_build(
                f"backlog:{dataset_id}",
                lambda: build_backlog(dataset_id)
            )
            # Subsequent calls in this request reuse the cached Backlog
            return backlog.get_all_charts()
    """
    cache = _request_cache_var.get()
    if cache is None:
        cache = RequestCache()
        _request_cache_var.set(cache)
    return cache


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for database connection.

    Provides a database connection that is properly closed after use.
    """
    conn = database.get_db()
    try:
        yield conn
    finally:
        conn.close()
