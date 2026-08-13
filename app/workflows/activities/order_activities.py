from temporalio import activity

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
        )#Find the order

        if order is None:
            raise ValueError(
                f"Order {order_id} not found"
            )

        return (
            f"Order {order.order_id} exists "
            f"with status '{order.status}'"
        )

    finally:
        db.close()


@activity.defn
async def update_order_status(
    order_id: int,
    new_status: str,
) -> str:
    db = SessionLocal()

    try:
        # Find the order
        order = (
            db.query(Order)
            .filter(Order.order_id == order_id)
            .first()
        )

        if order is None:
            raise ValueError(
                f"Order {order_id} not found"
            )

        # Remember the previous status
        old_status = order.status

        # Update order
        order.status = new_status

        # Record status history
        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status=new_status,
        )

        db.add(status_history)

        # Save both changes
        db.commit()

        # Refresh order from database
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