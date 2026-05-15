import logging
import os
import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import REGISTRY, generate_latest

from . import cors_config, database, logging_config, metrics
from .api import charts, config, data, flow, health, insights, trends

# Set up structured JSON logging
logging_config.setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Anansi", description="Jira/CSV backlog analytics dashboard")

# Configure CORS middleware with hardened settings (see cors_config.py for security rationale)
app.add_middleware(
    CORSMiddleware,
    **cors_config.get_cors_config(),
)


@app.middleware("http")
async def add_correlation_id_middleware(request: Request, call_next: Callable) -> any:
    """Middleware to add correlation ID to all requests."""
    # Get or create correlation ID from request header or generate new one
    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
    if not correlation_id:
        correlation_id = logging_config.get_or_create_correlation_id()
    else:
        logging_config.set_correlation_id(correlation_id)

    # Process request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add correlation ID to response header
    response.headers["X-Correlation-ID"] = correlation_id

    # Record metrics
    method = request.method
    endpoint = request.url.path
    status = response.status_code

    metrics.request_count.labels(method=method, endpoint=endpoint, status=status).inc()
    metrics.request_duration.labels(method=method, endpoint=endpoint).observe(process_time)

    return response


database.init_db(database.DB_PATH)

app.include_router(config.router)
app.include_router(data.router)
app.include_router(charts.router)
app.include_router(insights.router)
app.include_router(flow.router)
app.include_router(trends.router)
app.include_router(health.router)


@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(generate_latest(REGISTRY), media_type="text/plain; charset=utf-8")


_frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend-vue", "dist")
if os.path.isdir(_frontend_dir):
    app.mount(
        "/",
        StaticFiles(directory=_frontend_dir, html=True),
        name="static",
    )
