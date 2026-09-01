"""Request-scoped structured logging and Prometheus instrumentation."""

import json
import logging
import time
import uuid

from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware


# =========================================================
# REQUEST CORRELATION ID
# =========================================================

correlation_id: ContextVar[str] = ContextVar(
    "correlation_id",
    default="-",
)


# =========================================================
# PART A HTTP METRICS
# =========================================================

REQUEST_COUNT = Counter(
    "smartfoodops_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "smartfoodops_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
)


# =========================================================
# PART A ORDER METRICS
# =========================================================

ORDERS_PLACED = Counter(
    "smartfoodops_orders_placed_total",
    "Orders placed",
)

RIDER_ASSIGNMENT_FAILURES = Counter(
    "smartfoodops_rider_assignment_failures_total",
    "Rider assignment failures",
)


# =========================================================
# WEEK 5 AI METRICS
# =========================================================

AI_CALLS = Counter(
    "smartfoodops_ai_calls_total",
    "AI calls",
    ["assistance_type", "status"],
)

AI_FAILURES = Counter(
    "smartfoodops_ai_failures_total",
    "AI failures",
    ["assistance_type"],
)

AI_LATENCY = Histogram(
    "smartfoodops_ai_request_duration_seconds",
    "AI request duration in seconds",
    ["assistance_type"],
)


# =========================================================
# STRUCTURED LOGGING
# =========================================================

class JsonFormatter(logging.Formatter):

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:

        return json.dumps(
            {
                "timestamp": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "level": record.levelname,
                "logger": record.name,
                "correlation_id": correlation_id.get(),
                "message": record.getMessage(),
            }
        )


def configure_logging() -> None:

    handler = logging.StreamHandler()

    handler.setFormatter(
        JsonFormatter()
    )

    root = logging.getLogger()

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


# =========================================================
# CORRELATION + METRICS MIDDLEWARE
# =========================================================

class CorrelationAndMetricsMiddleware(
    BaseHTTPMiddleware
):

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):

        request_id = (
            request.headers.get(
                "X-Request-ID"
            )
            or uuid.uuid4().hex
        )

        token = correlation_id.set(
            request_id
        )

        started = time.perf_counter()

        response = None

        try:

            response = await call_next(
                request
            )

            return response

        finally:

            elapsed = (
                time.perf_counter()
                - started
            )

            path = request.url.path

            status = getattr(
                response,
                "status_code",
                500,
            )

            REQUEST_COUNT.labels(
                request.method,
                path,
                status,
            ).inc()

            REQUEST_LATENCY.labels(
                request.method,
                path,
            ).observe(
                elapsed
            )

            # Only add the header when a response
            # actually exists.
            if response is not None:

                response.headers[
                    "X-Request-ID"
                ] = request_id

            correlation_id.reset(
                token
            )