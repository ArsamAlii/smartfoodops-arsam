from temporalio import activity

from app.db.database import SessionLocal

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.menu_item import MenuItem
from app.models.order_status_history import OrderStatusHistory
from app.models.refund import Refund
from app.models.settlement import Settlement
from app.models.users import User

from app.services.rider_assignment_service import assign_available_rider


# ===========================================================
# Validate Order
# ===========================================================

@activity.defn
async def validate_order_workflow(
    order_id: int,
) -> str:

    print(f"Activity: validating order {order_id}")

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
        # Lock order
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
        # Verify current database state
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
        # Status history
        # ---------------------------------------------------

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status=new_status,
            actor="workflow",
        )

        db.add(status_history)

        # ===================================================
        # COMPLETED
        #
        # When an order is completed:
        #
        # 1. Create settlement
        # 2. Release the rider
        #
        # Both happen in the same DB transaction.
        # ===================================================

        if new_status == "completed":

            # ------------------------------------------------
            # Create settlement only once
            # ------------------------------------------------

            existing_settlement = (
                db.query(Settlement)
                .filter(
                    Settlement.order_id == order_id
                )
                .first()
            )

            if existing_settlement is None:

                db.add(
                    Settlement(
                        order_id=order_id,
                        restaurant_amount=order.total_amount,
                        rider_amount=0,
                    )
                )

            # ------------------------------------------------
            # Release rider
            #
            # Lock rider row before changing availability.
            # ------------------------------------------------

            if order.rider_id is not None:

                rider = (
                    db.query(User)
                    .filter(
                        User.user_id == order.rider_id,
                        User.role == "rider",
                    )
                    .with_for_update()
                    .first()
                )

                if rider is not None:

                    rider.is_available = True

                    print(
                        f"Activity: rider {rider.user_id} "
                        f"is now AVAILABLE after "
                        f"completing order {order_id}"
                    )

        # ---------------------------------------------------
        # Commit everything atomically
        # ---------------------------------------------------

        db.commit()

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


# ===========================================================
# Cancel / Reject Order
# Refund Payment + Release Stock
# ===========================================================

@activity.defn
async def cancel_order(
    order_id: int,
    expected_status: str,
    new_status: str,
) -> str:

    print(
        f"Activity: processing order {order_id} "
        f"from '{expected_status}' "
        f"to '{new_status}'"
    )

    db = SessionLocal()

    try:

        # ---------------------------------------------------
        # Lock order
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
        # Idempotency
        # ---------------------------------------------------

        if order.status in {
            "cancelled",
            "rejected",
        }:

            return (
                f"Order {order_id} "
                f"is already '{order.status}'"
            )

        # ---------------------------------------------------
        # Verify expected state
        # ---------------------------------------------------

        if order.status != expected_status:
            raise ValueError(
                f"Order {order_id} is currently "
                f"'{order.status}', expected "
                f"'{expected_status}'"
            )

        # ---------------------------------------------------
        # Validate requested final status
        # ---------------------------------------------------

        if new_status not in {
            "cancelled",
            "rejected",
        }:
            raise ValueError(
                f"Invalid cancellation status: "
                f"'{new_status}'"
            )

        old_status = order.status

        # ===================================================
        # 1. Release Reserved Stock
        # ===================================================

        order_items = (
            db.query(OrderItem)
            .filter(
                OrderItem.order_id == order_id
            )
            .all()
        )

        for order_item in order_items:

            menu_item = (
                db.query(MenuItem)
                .filter(
                    MenuItem.menu_item_id
                    == order_item.menu_item_id
                )
                .with_for_update()
                .first()
            )

            if menu_item is None:
                raise ValueError(
                    f"Menu item "
                    f"{order_item.menu_item_id} "
                    f"not found while releasing stock"
                )

            if menu_item.stock is not None:
                menu_item.stock += order_item.quantity

        # ===================================================
        # 2. Refund Payment
        # ===================================================

        payment = (
            db.query(Payment)
            .filter(
                Payment.order_id == order_id
            )
            .with_for_update()
            .first()
        )

        if payment is not None:

            if payment.payment_status == "authorized":

                payment.payment_status = "refunded"

                db.add(
                    Refund(
                        payment_id=payment.payment_id,
                        amount=payment.final_amount,
                        reason=new_status,
                    )
                )

            elif payment.payment_status == "refunded":
                pass

        # ===================================================
        # 3. Release Rider if necessary
        # ===================================================

        if order.rider_id is not None:

            rider = (
                db.query(User)
                .filter(
                    User.user_id == order.rider_id,
                    User.role == "rider",
                )
                .with_for_update()
                .first()
            )

            if rider is not None:
                rider.is_available = True

        # ===================================================
        # 4. Change Order Status
        # ===================================================

        order.status = new_status

        # ===================================================
        # 5. Create Status History
        # ===================================================

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status=new_status,
            actor="workflow",
            reason=new_status,
        )

        db.add(status_history)

        # ===================================================
        # 6. Commit Everything Atomically
        # ===================================================

        db.commit()

        db.refresh(order)

        return (
            f"Order {order_id} changed "
            f"from '{old_status}' "
            f"to '{new_status}'. "
            f"Payment refunded and stock released."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ===========================================================
# Automatic Rider Assignment
# ===========================================================

@activity.defn
async def assign_rider(
    order_id: int,
) -> int | None:

    """Atomically assign an available rider.

    Safe for Temporal retries and concurrent dispatchers.
    """

    db = SessionLocal()

    try:
        return assign_available_rider(
            db,
            order_id,
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()