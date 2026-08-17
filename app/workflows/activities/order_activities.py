from temporalio import activity

from app.db.database import SessionLocal

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.menu_item import MenuItem
from app.models.order_status_history import (
    OrderStatusHistory,
)


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
        # Lock order
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
        )

        db.add(status_history)

        # ---------------------------------------------------
        # Commit atomically
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
# Cancel Order
# Refund Payment + Release Stock
# ===========================================================

@activity.defn
async def cancel_order(
    order_id: int,
    expected_status: str,
) -> str:

    print(
        f"Activity: cancelling order {order_id} "
        f"from '{expected_status}'"
    )

    db = SessionLocal()

    try:

        # ---------------------------------------------------
        # Lock order
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
        # Idempotency
        # ---------------------------------------------------

        if order.status == "cancelled":

            print(
                f"Activity: order {order_id} "
                f"is already cancelled"
            )

            return (
                f"Order {order_id} "
                f"was already cancelled"
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

            menu_item.stock += order_item.quantity

            print(
                f"Activity: released "
                f"{order_item.quantity} units "
                f"of menu item "
                f"{order_item.menu_item_id}"
            )

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

                print(
                    f"Activity: payment "
                    f"{payment.payment_id} "
                    f"refunded"
                )

            elif payment.payment_status == "refunded":

                print(
                    f"Activity: payment "
                    f"{payment.payment_id} "
                    f"is already refunded"
                )

            else:

                print(
                    f"Activity: payment "
                    f"{payment.payment_id} "
                    f"has status "
                    f"'{payment.payment_status}'"
                )

        # ===================================================
        # 3. Change Order Status
        # ===================================================

        order.status = "cancelled"

        # ===================================================
        # 4. Create Status History
        # ===================================================

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status=old_status,
            to_status="cancelled",
        )

        db.add(status_history)

        # ===================================================
        # 5. Commit Everything Atomically
        # ===================================================

        db.commit()

        db.refresh(order)

        print(
            f"Activity completed: order {order_id} "
            f"is now 'cancelled'"
        )

        return (
            f"Order {order_id} cancelled. "
            f"Payment refunded and stock released."
        )

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()