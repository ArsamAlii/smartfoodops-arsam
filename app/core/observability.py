"""Request-scoped structured logging and Prometheus instrumentation."""

import json
import logging
import time
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware


correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
REQUEST_COUNT = Counter(
    "smartfoodops_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "smartfoodops_http_request_duration_seconds", "HTTP request duration", ["method", "path"]
)
ORDERS_PLACED = Counter("smartfoodops_orders_placed_total", "Orders placed")
RIDER_ASSIGNMENT_FAILURES = Counter(
    "smartfoodops_rider_assignment_failures_total", "Rider assignment failures"
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": correlation_id.get(),
            "message": record.getMessage(),
        })


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


class CorrelationAndMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or __import__("uuid").uuid4().hex
        token = correlation_id.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed = time.perf_counter() - started
            path = request.url.path
            status = getattr(locals().get("response"), "status_code", 500)
            REQUEST_COUNT.labels(request.method, path, status).inc()
            REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
            correlation_id.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
