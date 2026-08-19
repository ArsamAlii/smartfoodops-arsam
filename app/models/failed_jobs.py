from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FailedJob(Base):
    __tablename__ = "failed_jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    task_args: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    error: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    traceback: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    failed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )