from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.order import Order
from app.services.rider_assignment_service import assign_available_rider


@celery_app.task
def analytics_rollup():
    print("Running periodic analytics rollup")

    return "Analytics rollup completed"


@celery_app.task(bind=True, autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def requeue_waiting_orders(self):
    """Retry dispatch for READY orders; no rider means the order remains queued."""
    db = SessionLocal()
    try:
        order_ids = [row[0] for row in db.query(Order.order_id).filter(Order.status == "ready").all()]
        assigned = 0
        for order_id in order_ids:
            if assign_available_rider(db, order_id) is not None:
                assigned += 1
        return {"checked": len(order_ids), "assigned": assigned}
    finally:
        db.close()
