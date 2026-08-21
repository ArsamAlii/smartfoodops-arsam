from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped,mapped_column, relationship

from app.db.base import Base

class Restaurant(Base):
    __tablename__ = "restaurants"
    restaurant_id: Mapped[int] = mapped_column(primary_key=True)

    user_id:Mapped[int]=mapped_column(
        ForeignKey("users.user_id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    cuisine: Mapped[str] = mapped_column(
        String(50),
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    operating_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        default= True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default= datetime.utcnow,
        nullable=False,
    )

    owner: Mapped["User"] = relationship(
        back_populates="restaurants"
    )

    categories: Mapped[list["MenuCategory"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan"
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="restaurant"
    )
