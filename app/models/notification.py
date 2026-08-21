from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    recipient_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    recipient_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )