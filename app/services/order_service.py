from decimal import Decimal
from sqlalchemy.orm import Session, joinedload

from app.models.menu_item import MenuItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory
from app.models.payment import Payment
from app.models.restaurant import Restaurant
from app.schemas.order import OrderCreate

def create_order(
    db: Session,
    customer_id: int,
    order_data: OrderCreate,
) -> Order:

    try:
        # 1. Verify restaurant
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

        # 2. Verify restaurant is open
        if not restaurant.is_open:
            raise ValueError(
                "Restaurant is currently closed"
            )

        # 3. Create order
        order = Order(
            customer_id=customer_id,
            restaurant_id=order_data.restaurant_id,
            status="placed",
            total_amount=Decimal("0.00"),
        )

        db.add(order)
        db.flush()

        total_amount = Decimal("0.00")

        # 4. Process items
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

            if not menu_item:
                raise ValueError(
                    f"Menu item "
                    f"{item_data.menu_item_id} not found"
                )

            if (
                menu_item.category.restaurant_id
                != order_data.restaurant_id
            ):
                raise ValueError(
                    f"Menu item "
                    f"{item_data.menu_item_id} "
                    "does not belong to this restaurant"
                )

            if not menu_item.is_available:
                raise ValueError(
                    f"Menu item '{menu_item.name}' "
                    "is unavailable"
                )

            if menu_item.stock < item_data.quantity:
                raise ValueError(
                    f"Insufficient stock for "
                    f"'{menu_item.name}'"
                )

            unit_price = menu_item.price

            total_amount += (
                unit_price * item_data.quantity
            )

            order_item = OrderItem(
                order_id=order.order_id,
                menu_item_id=menu_item.menu_item_id,
                quantity=item_data.quantity,
                unit_price=unit_price,
            )

            db.add(order_item)

            # Stock reservation
            menu_item.stock -= item_data.quantity

        # 5. Set total
        order.total_amount = total_amount

        # 6. Calculate tax
        if order_data.payment_method.value == "cod":
            tax_percentage = Decimal("10.00")

        elif order_data.payment_method.value == "online":
            tax_percentage = Decimal("6.00")

        elif order_data.payment_method.value == "card":
            tax_percentage = Decimal("3.00")

        else:
            raise ValueError(
                "Unsupported payment method"
            )

        tax_amount = (
            total_amount
            * tax_percentage
            / Decimal("100")
        )

        final_amount = total_amount + tax_amount

        # 7. Create payment
        payment = Payment(
            order_id=order.order_id,
            payment_method=(
                order_data.payment_method.value
            ),
            tax_percentage=tax_percentage,
            tax_amount=tax_amount,
            final_amount=final_amount,
            payment_status="pending",
        )

        db.add(payment)

        # 8. Status history
        status_history = OrderStatusHistory(
            order_id=order.order_id,
            from_status="",
            to_status="placed",
        )

        db.add(status_history)

        # 9. Commit everything atomically
        db.commit()

        # 10. Reload relationships
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
        db.rollback()
        raise