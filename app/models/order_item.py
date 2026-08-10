from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    # -------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------
    order_item_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # -------------------------------------------------------
    # Order
    # -------------------------------------------------------
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
    )

    # -------------------------------------------------------
    # Menu Item
    # -------------------------------------------------------
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.menu_item_id"),
        nullable=False,
    )

    # -------------------------------------------------------
    # Quantity
    # -------------------------------------------------------
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # -------------------------------------------------------
    # Price at the Time of Ordering
    # -------------------------------------------------------
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # -------------------------------------------------------
    # Relationships
    # -------------------------------------------------------

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    menu_item: Mapped["MenuItem"] = relationship(
        "MenuItem",
        back_populates="order_items",
    )