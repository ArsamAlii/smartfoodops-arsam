from temporalio import activity
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import SessionLocal
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory


@activity.defn
async def validate_order_workflow(order_id: int) -> str:
    db = SessionLocal()

    try:
        order = (
            db.query(Order)
            .filter(Order.order_id == order_id)
            .first()
        )

        if order is None:
            raise ValueError(
                f"Order {order_id} not found"
            )

        return order.status

    finally:
        db.close()


@activity.defn
async def update_order_status(
    order_id: int,
    expected_status: str,
    new_status: str,
) -> str:

    db = SessionLocal()

    try:
        # ---------------------------------------------------
        # Find order
        # ---------------------------------------------------

        order = (
            db.query(Order)
            .filter(Order.order_id == order_id)
            .with_for_update()
            .first()
        )

        if order is None:
            raise ValueError(
                f"Order {order_id} not found"
            )

        # ---------------------------------------------------
        # Verify database state
        # ---------------------------------------------------

        if order.status != expected_status:
            raise ValueError(
                f"Order {order_id} is currently "
                f"'{order.status}', expected "
                f"'{expected_status}'"
            )

        old_status = order.status

        # ---------------------------------------------------
        # Update status
        # ---------------------------------------------------

        order.status = new_status

        # ---------------------------------------------------
        # Create status history
        # ---------------------------------------------------

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status=new_status,
        )

        db.add(status_history)

        # ---------------------------------------------------
        # Commit atomically
        # ---------------------------------------------------

        db.commit()

        db.refresh(order)

        return (
            f"Order {order_id} status changed "
            f"from '{old_status}' to '{new_status}'"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()