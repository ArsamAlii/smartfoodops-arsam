from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    # -------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------
    status_history_id: Mapped[int] = mapped_column(
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
    # Status Transition
    # -------------------------------------------------------
    from_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    to_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # -------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------
    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -------------------------------------------------------
    # Relationship
    # -------------------------------------------------------
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="status_history",
    )