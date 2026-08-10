from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"

    # -------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------
    payment_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # -------------------------------------------------------
    # Order
    # -------------------------------------------------------
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
        unique=True,
    )

    # -------------------------------------------------------
    # Payment Method
    # -------------------------------------------------------
    payment_method: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # -------------------------------------------------------
    # Tax
    # -------------------------------------------------------
    tax_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # -------------------------------------------------------
    # Final Amount
    # -------------------------------------------------------
    final_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # -------------------------------------------------------
    # Payment Status
    # -------------------------------------------------------
    payment_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
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
    # Relationship
    # -------------------------------------------------------
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="payment",
    )
