import os
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from app.models.idempotency_key import IdempotencyKey
from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.restaurant import Restaurant
from app.schemas.order import OrderCreate
from app.services.payment.payment_authorizer import (
    PaymentAuthorizer,
    PaymentAuthorizationError,
)


def create_order(
    db: Session,
    customer_id: int,
    order_data: OrderCreate,
    idempotency_key: str,
) -> Order:

    # -------------------------------------------------------
    # 1. Get Idempotency Key TTL
    # -------------------------------------------------------
    ttl_seconds = int(
        os.getenv(
            "IDEMPOTENCY_KEY_TTL_SECONDS",
            "86400",
        )
    )

    now = datetime.utcnow()

    # -------------------------------------------------------
    # 2. Check Existing Idempotency Key
    # -------------------------------------------------------
    existing_key = (
        db.query(IdempotencyKey)
        .filter(
            IdempotencyKey.key == idempotency_key,
            IdempotencyKey.customer_id == customer_id,
        )
        .first()
    )

    # -------------------------------------------------------
    # 3. Return Existing Order If Key Is Still Valid
    # -------------------------------------------------------
    if existing_key:

        if existing_key.expires_at > now:

            existing_order = (
                db.query(Order)
                .options(
                    joinedload(Order.payment),
                    joinedload(Order.items),
                )
                .filter(
                    Order.order_id == existing_key.order_id
                )
                .first()
            )

            if existing_order:
                return existing_order

        # Existing key has expired
        db.delete(existing_key)
        db.flush()

    try:

        # ---------------------------------------------------
        # 4. Verify Restaurant Exists
        # ---------------------------------------------------
        restaurant = (
            db.query(Restaurant)
            .filter(
                Restaurant.restaurant_id
                == order_data.restaurant_id
            )
            .first()
        )

        if not restaurant:
            raise ValueError("Restaurant not found")

        # ---------------------------------------------------
        # 5. Verify Restaurant Is Open
        # ---------------------------------------------------
        if not restaurant.is_open:
            raise ValueError(
                "Restaurant is currently closed"
            )

        # ---------------------------------------------------
        # 6. Create Order
        # ---------------------------------------------------
        order = Order(
            customer_id=customer_id,
            restaurant_id=order_data.restaurant_id,
            status="placed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        total_amount = Decimal("0.00")

        # ---------------------------------------------------
        # 7. Process Order Items
        # ---------------------------------------------------
        for item_data in order_data.items:

            menu_item = (
                db.query(MenuItem)
                .filter(
                    MenuItem.menu_item_id
                    == item_data.menu_item_id
                )
                .with_for_update()
                .first()
            )

            # ------------------------------------------------
            # 8. Verify Menu Item Exists
            # ------------------------------------------------
            if not menu_item:
                raise ValueError(
                    f"Menu item "
                    f"{item_data.menu_item_id} not found"
                )

            # ------------------------------------------------
            # 9. Verify Item Belongs To Restaurant
            # ------------------------------------------------
            if (
                menu_item.category.restaurant_id
                != order_data.restaurant_id
            ):
                raise ValueError(
                    f"Menu item "
                    f"{item_data.menu_item_id} "
                    "does not belong to this restaurant"
                )

            # ------------------------------------------------
            # 10. Verify Availability
            # ------------------------------------------------
            if not menu_item.is_available:
                raise ValueError(
                    f"Menu item '{menu_item.name}' "
                    "is unavailable"
                )

            # ------------------------------------------------
            # 11. Verify Stock
            # ------------------------------------------------
            if menu_item.stock < item_data.quantity:
                raise ValueError(
                    f"Insufficient stock for "
                    f"'{menu_item.name}'"
                )

            # ------------------------------------------------
            # 12. Server-Side Price
            # ------------------------------------------------
            unit_price = menu_item.price

            item_total = (
                unit_price * item_data.quantity
            )

            total_amount += item_total

            # ------------------------------------------------
            # 13. Create Order Item
            # ------------------------------------------------
            order_item = OrderItem(
                order_id=order.order_id,
                menu_item_id=menu_item.menu_item_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
            )

            db.add(order_item)

            # ------------------------------------------------
            # 14. Reserve Stock
            # ------------------------------------------------
            menu_item.stock -= item_data.quantity

        # ---------------------------------------------------
        # 15. Set Order Total
        # ---------------------------------------------------
        order.total_amount = total_amount

        # ---------------------------------------------------
        # 16. Authorize Payment
        # ---------------------------------------------------
        authorizer = PaymentAuthorizer(db)

        try:
            authorizer.authorize(
                order=order,
                idempotency_key=idempotency_key,
                payment_method=(
                    order_data.payment_method.value
                ),
            )

        except PaymentAuthorizationError as exc:

            # Payment failed.
            # Because the entire operation is inside the
            # same transaction, the order and stock changes
            # will be rolled back below.
            raise ValueError(str(exc))

        # ---------------------------------------------------
        # 17. Create Initial Status History
        # ---------------------------------------------------
        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status="",
            to_status="placed",
        )

        db.add(status_history)

        # ---------------------------------------------------
        # 18. Save Idempotency Record
        # ---------------------------------------------------
        idempotency_record = IdempotencyKey(
            key=idempotency_key,
            customer_id=customer_id,
            order_id=order.order_id,
            created_at=now,
            expires_at=(
                now + timedelta(seconds=ttl_seconds)
            ),
        )

        db.add(idempotency_record)

        # ---------------------------------------------------
        # 19. Commit Everything Atomically
        # ---------------------------------------------------
        db.commit()

        # ---------------------------------------------------
        # 20. Reload Order With Relationships
        # ---------------------------------------------------
        order = (
            db.query(Order)
            .options(
                joinedload(Order.payment),
                joinedload(Order.items),
            )
            .filter(
                Order.order_id == order.order_id
            )
            .first()
        )

        return order

    except Exception:
        # ---------------------------------------------------
        # Rollback Entire Transaction
        # ---------------------------------------------------
        db.rollback()
        raise