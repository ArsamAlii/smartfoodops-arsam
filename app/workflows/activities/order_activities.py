from temporalio import activity

from app.db.database import SessionLocal
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory


# ===========================================================
# Validate Order
# ===========================================================

@activity.defn
async def validate_order_workflow(
    order_id: int,
) -> str:

    print(
        f"Activity: validating order {order_id}"
    )

    db = SessionLocal()

    try:
        order = (
            db.query(Order)
            .filter(
                Order.order_id == order_id
            )
            .first()
        )

        if order is None:
            raise ValueError(
                f"Order {order_id} not found"
            )

        print(
            f"Activity: order {order_id} "
            f"current status = '{order.status}'"
        )

        return order.status

    finally:
        db.close()


# ===========================================================
# Update Order Status
# ===========================================================

@activity.defn
async def update_order_status(
    order_id: int,
    expected_status: str,
    new_status: str,
) -> str:

    print(
        f"Activity: updating order {order_id} "
        f"from '{expected_status}' "
        f"to '{new_status}'"
    )

    db = SessionLocal()

    try:

        # ---------------------------------------------------
        # Find order
        # ---------------------------------------------------

        order = (
            db.query(Order)
            .filter(
                Order.order_id == order_id
            )
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

        # ---------------------------------------------------
        # Refresh order
        # ---------------------------------------------------

        db.refresh(order)

        print(
            f"Activity completed: order {order_id} "
            f"is now '{order.status}'"
        )

        return (
            f"Order {order_id} status changed "
            f"from '{old_status}' "
            f"to '{new_status}'"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()