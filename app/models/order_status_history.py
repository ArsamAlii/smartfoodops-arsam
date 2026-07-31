from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    status_history_id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.order_id"),
        nullable=False,
    )

    from_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    to_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

order: Mapped["Order"] = relationship(
    back_populates="status_history"
)