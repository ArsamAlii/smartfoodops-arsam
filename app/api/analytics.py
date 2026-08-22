from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.analytics import AnalyticsDaily


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/daily")
def get_daily_analytics(
    db: Session = Depends(get_db),
):
    """
    Return the latest daily analytics aggregate.
    """

    analytics = (
        db.query(AnalyticsDaily)
        .order_by(AnalyticsDaily.analytics_date.desc())
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
        "total_revenue": float(analytics.total_revenue),
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
            AnalyticsDaily.analytics_date == analytics_date
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
        "total_revenue": float(analytics.total_revenue),
        "average_order_value": float(
            analytics.average_order_value
        ),
        "failed_events": analytics.failed_events,
        "updated_at": analytics.updated_at,
    }