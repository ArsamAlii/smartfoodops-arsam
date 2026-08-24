from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.analytics import AnalyticsDaily
from app.models.failed_jobs import FailedJob
from app.models.order import Order


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# -------------------------------------------------------
# Daily Analytics
# -------------------------------------------------------

@router.get("/daily")
def get_daily_analytics(
    db: Session = Depends(get_db),
):
    """
    Return the latest daily analytics aggregate.
    """

    analytics = (
        db.query(AnalyticsDaily)
        .order_by(
            AnalyticsDaily.analytics_date.desc()
        )
        .first()
    )

    if analytics is None:
        raise HTTPException(
            status_code=404,
            detail="No analytics data available",
        )

    return {
        "date": analytics.analytics_date,
        "total_orders": analytics.total_orders,
        "completed_orders": analytics.completed_orders,
        "cancelled_orders": analytics.cancelled_orders,
        "total_revenue": float(
            analytics.total_revenue
        ),
        "average_order_value": float(
            analytics.average_order_value
        ),
        "failed_events": analytics.failed_events,
        "updated_at": analytics.updated_at,
    }


@router.get("/daily/{analytics_date}")
def get_daily_analytics_by_date(
    analytics_date: str,
    db: Session = Depends(get_db),
):
    """
    Return analytics for a specific date.
    """

    analytics = (
        db.query(AnalyticsDaily)
        .filter(
            AnalyticsDaily.analytics_date
            == analytics_date
        )
        .first()
    )

    if analytics is None:
        raise HTTPException(
            status_code=404,
            detail=f"No analytics found for {analytics_date}",
        )

    return {
        "date": analytics.analytics_date,
        "total_orders": analytics.total_orders,
        "completed_orders": analytics.completed_orders,
        "cancelled_orders": analytics.cancelled_orders,
        "total_revenue": float(
            analytics.total_revenue
        ),
        "average_order_value": float(
            analytics.average_order_value
        ),
        "failed_events": analytics.failed_events,
        "updated_at": analytics.updated_at,
    }


# -------------------------------------------------------
# Reconciliation
# -------------------------------------------------------

@router.get("/reconciliation/{analytics_date}")
def reconcile_analytics(
    analytics_date: str,
    db: Session = Depends(get_db),
):
    """
    Compare the analytics aggregate against the
    underlying raw database tables.

    This detects drift between analytics_daily and
    the source-of-truth operational tables.
    """

    # ---------------------------------------------------
    # Validate date
    # ---------------------------------------------------

    try:
        target_date = datetime.strptime(
            analytics_date,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    # ---------------------------------------------------
    # Get analytics aggregate
    # ---------------------------------------------------

    analytics = (
        db.query(AnalyticsDaily)
        .filter(
            AnalyticsDaily.analytics_date
            == analytics_date
        )
        .first()
    )

    if analytics is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No analytics aggregate found "
                f"for {analytics_date}"
            ),
        )

    # ---------------------------------------------------
    # Calculate raw total orders
    # ---------------------------------------------------

    raw_total_orders = (
        db.query(
            func.count(Order.order_id)
        )
        .filter(
            func.date(Order.created_at)
            == target_date
        )
        .scalar()
        or 0
    )

    # ---------------------------------------------------
    # Calculate raw completed orders
    # ---------------------------------------------------

    raw_completed_orders = (
        db.query(
            func.count(Order.order_id)
        )
        .filter(
            func.date(Order.created_at)
            == target_date,
            Order.status == "completed",
        )
        .scalar()
        or 0
    )

    # ---------------------------------------------------
    # Calculate raw cancelled orders
    # ---------------------------------------------------

    raw_cancelled_orders = (
        db.query(
            func.count(Order.order_id)
        )
        .filter(
            func.date(Order.created_at)
            == target_date,
            Order.status == "cancelled",
        )
        .scalar()
        or 0
    )

    # ---------------------------------------------------
    # Calculate raw revenue
    # ---------------------------------------------------

    raw_total_revenue = (
        db.query(
            func.coalesce(
                func.sum(Order.total_amount),
                0,
            )
        )
        .filter(
            func.date(Order.created_at)
            == target_date,
            Order.status == "completed",
        )
        .scalar()
        or 0
    )

    # ---------------------------------------------------
    # Calculate raw average order value
    # ---------------------------------------------------

    raw_average_order_value = (
        raw_total_revenue / raw_completed_orders
        if raw_completed_orders
        else 0
    )

    # ---------------------------------------------------
    # Failed jobs
    #
    # Note:
    # failed_jobs currently represents the DLQ.
    # The existing analytics rollup counts all failed
    # jobs, so reconciliation uses the same definition.
    # ---------------------------------------------------

    raw_failed_events = (
        db.query(
            func.count(FailedJob.task_id)
        )
        .scalar()
        or 0
    )

    # ---------------------------------------------------
    # Build raw values
    # ---------------------------------------------------

    raw = {
        "total_orders": raw_total_orders,
        "completed_orders": raw_completed_orders,
        "cancelled_orders": raw_cancelled_orders,
        "total_revenue": float(
            raw_total_revenue
        ),
        "average_order_value": float(
            raw_average_order_value
        ),
        "failed_events": raw_failed_events,
    }

    # ---------------------------------------------------
    # Build aggregate values
    # ---------------------------------------------------

    aggregate = {
        "total_orders": analytics.total_orders,
        "completed_orders": analytics.completed_orders,
        "cancelled_orders": analytics.cancelled_orders,
        "total_revenue": float(
            analytics.total_revenue
        ),
        "average_order_value": float(
            analytics.average_order_value
        ),
        "failed_events": analytics.failed_events,
    }

    # ---------------------------------------------------
    # Calculate drift
    # ---------------------------------------------------

    drift = {
        key: raw[key] - aggregate[key]
        for key in raw
    }

    # ---------------------------------------------------
    # Determine reconciliation status
    # ---------------------------------------------------

    matched = all(
        value == 0
        for value in drift.values()
    )

    # ---------------------------------------------------
    # Return reconciliation report
    # ---------------------------------------------------

    return {
        "date": analytics_date,
        "status": (
            "matched"
            if matched
            else "drift_detected"
        ),
        "aggregate": aggregate,
        "raw": raw,
        "drift": drift,
        "analytics_updated_at": (
            analytics.updated_at
        ),
    }