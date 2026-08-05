from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from datetime import datetime
from sqlalchemy import DateTime

class MenuCategory(Base):
    __tablename__="menu_categories"

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    category_id: Mapped[int]= mapped_column(primary_key=True)

    restaurant_id: Mapped[int]= mapped_column(
        ForeignKey("restaurants.restaurant_id"),
        nullable=False,
    )

    name:Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    ) 

    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    restaurant: Mapped["Restaurant"] = relationship(
        back_populates="categories"
    )

    menu_items: Mapped[list["MenuItem"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )