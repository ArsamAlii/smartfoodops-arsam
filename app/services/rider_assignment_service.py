from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.order import Order
from app.models.order_status_history import OrderStatusHistory
from app.models.users import User


def assign_available_rider(db: Session, order_id: int) -> int | None:
    """Atomically claim one available rider for a READY order.

    The order and rider rows are locked in one transaction.  ``skip_locked``
    lets concurrent dispatchers move on rather than both seeing the same rider.
    """
    order = (
        db.query(Order).filter(Order.order_id == order_id).with_for_update().first()
    )
    if order is None:
        raise ValueError("Order not found")
    if order.status == "assigned":
        return order.rider_id
    if order.status != "ready":
        return None
    rider = (
        db.query(User)
        .filter(User.role == UserRole.RIDER, User.is_available.is_(True))
        .order_by(User.user_id)
        .with_for_update(skip_locked=True)
        .first()
    )
    if rider is None:
        return None
    rider.is_available = False
    order.rider_id = rider.user_id
    order.status = "assigned"
    db.add(OrderStatusHistory(
        order_id=order.order_id, from_status="ready", to_status="assigned",
        actor="dispatch", reason="Available rider claimed atomically",
    ))
    db.commit()
    return rider.user_id
