from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    idempotency_key_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        "Order",
    )

    __table_args__ = (
        UniqueConstraint(
            "key",
            "customer_id",
            name="uq_idempotency_key_customer",
        ),
    )