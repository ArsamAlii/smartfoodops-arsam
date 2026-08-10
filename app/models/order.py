from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    # -------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------
    order_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # -------------------------------------------------------
    # Customer
    # -------------------------------------------------------
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    # -------------------------------------------------------
    # Restaurant
    # -------------------------------------------------------
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.restaurant_id"),
        nullable=False,
    )

    # -------------------------------------------------------
    # Rider
    # -------------------------------------------------------
    rider_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
    )

    # -------------------------------------------------------
    # Order Status
    # -------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(30),
        default="placed",
        nullable=False,
    )

    # -------------------------------------------------------
    # Total Amount
    # -------------------------------------------------------
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # -------------------------------------------------------
    # Audit Information
    # -------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -------------------------------------------------------
    # Relationships
    # -------------------------------------------------------

    customer: Mapped["User"] = relationship(
        "User",
        back_populates="customer_orders",
        foreign_keys=[customer_id],
    )

    rider: Mapped["User | None"] = relationship(
        "User",
        back_populates="assigned_orders",
        foreign_keys=[rider_id],
    )

    restaurant: Mapped["Restaurant"] = relationship(
        "Restaurant",
        back_populates="orders",
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    payment: Mapped["Payment | None"] = relationship(
        "Payment",
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
    )