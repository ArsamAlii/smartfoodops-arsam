import socket
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from app.api.payments import router as payments_router
from app.db.database import engine
from app.db.base import Base
from app.api.orders import router as orders_router
# -------------------------------------------------------
# Models
# -------------------------------------------------------
import app.models.users
import app.models.restaurant
import app.models.menu_category
import app.models.menu_item
import app.models.order
import app.models.order_item
import app.models.order_status_history
import app.models.payment
import app.models.content_chunk
import app.models.refund
import app.models.settlement
import app.models.notification
import app.models.processed_event
import app.models.analytics
# -------------------------------------------------------
# API Routers
# -------------------------------------------------------
from app.api.auth import router as auth_router
from app.api.restaurant import router as restaurant_router
from app.api.menu_category import router as menu_category_router
from app.api.menu_item import router as menu_item_router
from app.api.orders import router as orders_router
from app.api.users import router as users_router
from app.api.failed_jobs import router as failed_jobs_router
from app.api.celery import router as celery_router
from app.core.observability import CorrelationAndMetricsMiddleware, configure_logging
from app.db.database import SessionLocal
from app.api.analytics import router as analytics_router
from app.api.search import router as search_router
from app.api.ai import router as ai_router
from app.api.ai_analytics import router as ai_analytics_router
from app.api.restaurant_generation import router as restaurant_generation_router
# Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0",
)
configure_logging()
app.add_middleware(CorrelationAndMetricsMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger(__name__).exception("Unhandled request error")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "Internal server error"}},
    )


# -------------------------------------------------------
# Routers
# -------------------------------------------------------
app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(menu_category_router)
app.include_router(menu_item_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(users_router)
app.include_router(failed_jobs_router)
app.include_router(celery_router)
app.include_router(analytics_router)
app.include_router(search_router)
app.include_router(ai_router)
app.include_router(restaurant_generation_router)
app.include_router(ai_analytics_router)
# -------------------------------------------------------
# Root
# -------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to SmartFoodOps API"
    }


# -------------------------------------------------------
# Health
# -------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/health/ready")
def readiness():
    """Readiness verifies the dependencies needed to accept work."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        redis_url = __import__("os").environ.get("REDIS_URL", "redis://localhost:6379/0")
        import redis
        redis.Redis.from_url(redis_url, socket_connect_timeout=1).ping()
        kafka_host, kafka_port = __import__("os").environ.get(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"
        ).split(",")[0].split(":")
        with socket.create_connection((kafka_host, int(kafka_port)), timeout=1):
            pass
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Dependencies are not ready") from exc
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# -------------------------------------------------------
# Identify
# -------------------------------------------------------
@app.get("/identify")
def identify_me():
    return {
        "name": "arsam"
    }
