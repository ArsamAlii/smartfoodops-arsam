from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey,String
from sqlalpchemy.orm import Mapped,Mapped_column

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

    cuisine: Mapped[str] = mapped_column(
        String(50),
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_open: Mapped[bool] = mapped_column(
        Boolean,
        default= True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default= datetime.utcnow,
        nullable=False,
    )