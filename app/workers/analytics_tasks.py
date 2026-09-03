from datetime import datetime

from sqlalchemy import func

from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.order import Order
from app.models.analytics import AnalyticsDaily
from app.models.failed_jobs import FailedJob

from app.workflows.temporal_client import signal_order_workflow


@celery_app.task
def analytics_rollup():

    print("Running periodic analytics rollup")

    db = SessionLocal()

    try:

        today = datetime.utcnow().date()
        today_string = today.isoformat()

        total_orders = (
            db.query(func.count(Order.order_id))
            .filter(
                func.date(Order.created_at) == today
            )
            .scalar()
            or 0
        )

        completed_orders = (
            db.query(func.count(Order.order_id))
            .filter(
                func.date(Order.created_at) == today,
                Order.status == "completed",
            )
            .scalar()
            or 0
        )

        cancelled_orders = (
            db.query(func.count(Order.order_id))
            .filter(
                func.date(Order.created_at) == today,
                Order.status == "cancelled",
            )
            .scalar()
            or 0
        )

        total_revenue = (
            db.query(
                func.coalesce(
                    func.sum(Order.total_amount),
                    0,
                )
            )
            .filter(
                func.date(Order.created_at) == today,
                Order.status == "completed",
            )
            .scalar()
            or 0
        )

        average_order_value = (
            total_revenue / completed_orders
            if completed_orders
            else 0
        )

        failed_events = (
            db.query(
                func.count(FailedJob.task_id)
            )
            .scalar()
            or 0
        )

        analytics = (
            db.query(AnalyticsDaily)
            .filter(
                AnalyticsDaily.analytics_date
                == today_string
            )
            .first()
        )

        if analytics is None:

            analytics = AnalyticsDaily(
                analytics_date=today_string
            )

            db.add(analytics)

        analytics.total_orders = total_orders
        analytics.completed_orders = completed_orders
        analytics.cancelled_orders = cancelled_orders
        analytics.total_revenue = total_revenue
        analytics.average_order_value = average_order_value
        analytics.failed_events = failed_events
        analytics.updated_at = datetime.utcnow()

        db.commit()

        print(
            f"Analytics updated: "
            f"date={today_string}, "
            f"total_orders={total_orders}, "
            f"completed_orders={completed_orders}, "
            f"cancelled_orders={cancelled_orders}, "
            f"revenue={total_revenue}, "
            f"average_order_value={average_order_value}, "
            f"failed_events={failed_events}"
        )

        return {
            "date": today_string,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": float(total_revenue),
            "average_order_value": float(
                average_order_value
            ),
            "failed_events": failed_events,
        }

    finally:
        db.close()


# ===========================================================
# Requeue Waiting Orders
# ===========================================================

@celery_app.task(
    bind=True,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
    max_retries=3,
)
def requeue_waiting_orders(self):

    """Ask Temporal to retry rider assignment for READY orders."""

    db = SessionLocal()

    try:

        order_ids = [
            row[0]
            for row in (
                db.query(Order.order_id)
                .filter(
                    Order.status == "ready"
                )
                .all()
            )
        ]

    finally:

        db.close()

    checked = len(order_ids)
    signalled = 0

    # -------------------------------------------------------
    # Tell each READY order's Temporal workflow to retry
    # dispatch.
    # -------------------------------------------------------

    for order_id in order_ids:

        try:

            import asyncio

            asyncio.run(
                signal_order_workflow(
                    order_id=order_id,
                    status="assigned",
                )
            )

            signalled += 1

            print(
                f"Requeue: signalled order {order_id} "
                f"for automatic rider assignment"
            )

        except Exception as exc:

            print(
                f"Requeue: could not signal order "
                f"{order_id}: {exc}"
            )

    return {
        "checked": checked,
        "signalled": signalled,
    }