"""Prometheus metrics definitions for Anansi observability."""

import logging
import time
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Request metrics
request_count = Counter(
    "anansi_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

request_duration = Histogram(
    "anansi_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Error metrics
errors_total = Counter(
    "anansi_errors_total",
    "Total errors encountered",
    ["error_type"],
)

# Database metrics
db_pool_connections = Gauge(
    "anansi_db_pool_size",
    "Current active database connections",
)

# Cache metrics
cache_hits = Counter(
    "anansi_cache_hits_total",
    "Total cache hits",
    ["cache_name"],
)

cache_misses = Counter(
    "anansi_cache_misses_total",
    "Total cache misses",
    ["cache_name"],
)


def track_metrics(endpoint: str | None = None):
    """Decorator to track request metrics.

    Args:
        endpoint: Optional endpoint name for metrics labeling
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ep_name = endpoint or func.__name__
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                errors_total.labels(error_type=type(e).__name__).inc()
                raise
            finally:
                duration = time.time() - start_time
                request_duration.labels(method="GET", endpoint=ep_name).observe(duration)

        return wrapper

    return decorator
