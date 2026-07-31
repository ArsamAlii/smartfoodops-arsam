from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True)

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.restaurant_id"),
        nullable=False,
    )

    rider_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=True,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


    customer: Mapped["User"] = relationship(
        back_populates="customer_orders",
        foreign_keys=[customer_id]
    )

    rider: Mapped["User"] = relationship(
        back_populates="assigned_orders",
        foreign_keys=[rider_id]
    )

    restaurant: Mapped["Restaurant"] = relationship(
        back_populates="orders"
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

    payment: Mapped["Payment"] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )