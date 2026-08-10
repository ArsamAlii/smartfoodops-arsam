```python
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.restaurant import Restaurant
from app.schemas.order import OrderCreate


def create_order(
    db: Session,
    customer_id: int,
    order_data: OrderCreate,
) -> Order:
    # -------------------------------------------------------
    # 1. Verify restaurant exists
    # -------------------------------------------------------
    restaurant = (
        db.query(Restaurant)
        .filter(
            Restaurant.restaurant_id == order_data.restaurant_id
        )
        .first()
    )

    if not restaurant:
        raise ValueError("Restaurant not found")

    # -------------------------------------------------------
    # 2. Verify restaurant is open
    # -------------------------------------------------------
    if not restaurant.is_open:
        raise ValueError("Restaurant is currently closed")

    # -------------------------------------------------------
    # 3. Create Order
    # -------------------------------------------------------
    order = Order(
        customer_id=customer_id,
        restaurant_id=order_data.restaurant_id,
        status="placed",
        total_amount=Decimal("0.00"),
    )

    db.add(order)
    db.flush()

    total_amount = Decimal("0.00")

    # -------------------------------------------------------
    # 4. Process each order item
    # -------------------------------------------------------
    for item_data in order_data.items:

        menu_item = (
            db.query(MenuItem)
            .filter(
                MenuItem.menu_item_id == item_data.menu_item_id
            )
            .first()
        )

        # ---------------------------------------------------
        # 5. Verify menu item exists
        # ---------------------------------------------------
        if not menu_item:
            raise ValueError(
                f"Menu item {item_data.menu_item_id} not found"
            )

        # ---------------------------------------------------
        # 6. Verify menu item belongs to restaurant
        # ---------------------------------------------------
        if (
            menu_item.category.restaurant_id
            != order_data.restaurant_id
        ):
            raise ValueError(
                f"Menu item {item_data.menu_item_id} "
                "does not belong to this restaurant"
            )

        # ---------------------------------------------------
        # 7. Verify item is available
        # ---------------------------------------------------
        if not menu_item.is_available:
            raise ValueError(
                f"Menu item '{menu_item.name}' is unavailable"
            )

        # ---------------------------------------------------
        # 8. Verify stock
        # ---------------------------------------------------
        if menu_item.stock < item_data.quantity:
            raise ValueError(
                f"Insufficient stock for '{menu_item.name}'"
            )

        # ---------------------------------------------------
        # 9. Calculate price from database
        # ---------------------------------------------------
        unit_price = menu_item.price

        item_total = (
            unit_price * item_data.quantity
        )

        total_amount += item_total

        # ---------------------------------------------------
        # 10. Create OrderItem
        # ---------------------------------------------------
        order_item = OrderItem(
            order_id=order.order_id,
            menu_item_id=menu_item.menu_item_id,
            quantity=item_data.quantity,
            unit_price=unit_price,
        )

        db.add(order_item)

        # ---------------------------------------------------
        # 11. Reduce stock
        # ---------------------------------------------------
        menu_item.stock -= item_data.quantity

    # -------------------------------------------------------
    # 12. Set calculated total
    # -------------------------------------------------------
    order.total_amount = total_amount

    # -------------------------------------------------------
    # 13. Create initial status history
    # -------------------------------------------------------
    status_history = OrderStatusHistory(
        order_id=order.order_id,
        from_status="",
        to_status="placed",
    )

    db.add(status_history)

    # -------------------------------------------------------
    # 14. Commit transaction
    # -------------------------------------------------------
    db.commit()

    # -------------------------------------------------------
    # 15. Refresh order
    # -------------------------------------------------------
    db.refresh(order)

    return order
```
