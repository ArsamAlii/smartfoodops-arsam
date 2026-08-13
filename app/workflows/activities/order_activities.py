from temporalio import activity

from app.db.database import SessionLocal
from app.models.order import Order


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

        return (
            f"Order {order.order_id} exists "
            f"with status '{order.status}'"
        )

    finally:
        db.close()