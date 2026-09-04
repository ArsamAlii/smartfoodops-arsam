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
from app.services.redis_service import (
    get_idempotency_key,
    set_idempotency_key,
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
    # 2. Check Redis Idempotency Key
    # -------------------------------------------------------

    redis_order_id = get_idempotency_key(
        customer_id=customer_id,
        idempotency_key=idempotency_key,
    )

    if redis_order_id:

        existing_order = (
            db.query(Order)
            .options(
                joinedload(Order.payment),
                joinedload(Order.items),
            )
            .filter(
                Order.order_id == int(redis_order_id)
            )
            .first()
        )

        if existing_order:
            return existing_order

    # -------------------------------------------------------
    # 3. Check PostgreSQL Idempotency Key
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
    # 4. Return Existing Order If Key Is Still Valid
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

        db.delete(existing_key)
        db.flush()
 
    try:

        # ===================================================
        # 5. Verify Restaurant
        # ===================================================

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

        if not restaurant.is_open:
            raise ValueError(
                "Restaurant is currently closed"
            )

        # ===================================================
        # 6. VALIDATE ALL ITEMS FIRST
        # ===================================================

        validation_errors = []
        validated_items = []

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
            # Item does not exist
            # ------------------------------------------------

            if not menu_item:

                validation_errors.append(
                    f"Menu item "
                    f"{item_data.menu_item_id} not found"
                )

                continue

            # ------------------------------------------------
            # Item belongs to another restaurant
            # ------------------------------------------------

            if (
                menu_item.category.restaurant_id
                != order_data.restaurant_id
            ):

                validation_errors.append(
                    f"Menu item "
                    f"{item_data.menu_item_id} "
                    "does not belong to this restaurant"
                )

                continue

            # ------------------------------------------------
            # Item unavailable
            # ------------------------------------------------

            if not menu_item.is_available:

                validation_errors.append(
                    f"Menu item '{menu_item.name}' "
                    "is unavailable"
                )

                continue

            # ------------------------------------------------
            # Invalid quantity
            # ------------------------------------------------

            if item_data.quantity <= 0:

                validation_errors.append(
                    f"Invalid quantity for "
                    f"'{menu_item.name}'. "
                    "Quantity must be greater than zero."
                )

                continue

            # ------------------------------------------------
            # Insufficient stock
            # ------------------------------------------------

            if (
                menu_item.stock is not None
                and menu_item.stock < item_data.quantity
            ):

                validation_errors.append(
                    f"Insufficient stock for "
                    f"'{menu_item.name}'. "
                    f"Available: {menu_item.stock}, "
                    f"requested: {item_data.quantity}"
                )

                continue

            # ------------------------------------------------
            # Everything is valid
            # ------------------------------------------------

            validated_items.append(
                (
                    item_data,
                    menu_item,
                )
            )

        # ===================================================
        # 7. Return ALL Validation Errors At Once
        # ===================================================

        if validation_errors:

            raise ValueError(
                "Order validation failed: "
                + " | ".join(validation_errors)
            )

        # ===================================================
        # 8. Create Order
        # ===================================================

        order = Order(
            customer_id=customer_id,
            restaurant_id=order_data.restaurant_id,
            status="placed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        total_amount = Decimal("0.00")

        # ===================================================
        # 9. Process Validated Items
        # ===================================================

        for item_data, menu_item in validated_items:

            # ------------------------------------------------
            # Server-side price
            # ------------------------------------------------

            unit_price = menu_item.price

            item_total = (
                unit_price * item_data.quantity
            )

            total_amount += item_total

            # ------------------------------------------------
            # Create Order Item
            # ------------------------------------------------

            order_item = OrderItem(
                order_id=order.order_id,
                menu_item_id=menu_item.menu_item_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
            )

            db.add(order_item)

            # ------------------------------------------------
            # Reserve Stock
            # ------------------------------------------------

            if menu_item.stock is not None:

                print(
                    f"[STOCK DEBUG] Order {order.order_id}: "
                    f"menu_item={menu_item.menu_item_id}, "
                    f"stock BEFORE={menu_item.stock}, "
                    f"quantity={item_data.quantity}"
                )

                menu_item.stock -= item_data.quantity

                print(
                    f"[STOCK DEBUG] Order {order.order_id}: "
                    f"menu_item={menu_item.menu_item_id}, "
                    f"stock AFTER={menu_item.stock}"
                )

        # ===================================================
        # 10. Set Server-Side Order Total
        # ===================================================

        order.total_amount = total_amount

        # ===================================================
        # 11. Authorize Payment
        # ===================================================

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

            # Entire transaction is rolled back below.
            raise ValueError(str(exc))

        # ===================================================
        # 12. Initial Status History
        # ===================================================

        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status="",
            to_status="placed",
            actor="customer",
            reason="Order submitted",
        )

        db.add(status_history)

        # ===================================================
        # 13. Save Idempotency Record
        # ===================================================

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

        # ===================================================
        # 14. Debug Before Commit
        # ===================================================

        if validated_items:

            debug_item = validated_items[0][1]

            print(
                f"[STOCK DEBUG] COMMITTING ORDER "
                f"{order.order_id}: "
                f"menu_item={debug_item.menu_item_id}, "
                f"stock={debug_item.stock}"
            )

        # ===================================================
        # 15. Commit Everything Atomically
        # ===================================================

        db.commit()

        print(
            f"[STOCK DEBUG] COMMIT SUCCESS "
            f"for order {order.order_id}"
        )

        # ===================================================
        # 16. Save Redis Idempotency Key
        # ===================================================

        try:

            set_idempotency_key(
                customer_id=customer_id,
                idempotency_key=idempotency_key,
                order_id=order.order_id,
                ttl_seconds=ttl_seconds,
            )

        except Exception as exc:

            print(
                f"Warning: failed to store "
                f"idempotency key in Redis: {exc}"
            )

        # ===================================================
        # 17. Reload Order
        # ===================================================

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
        # Rollback EVERYTHING
        # ---------------------------------------------------

        db.rollback()
        raise
