from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class MenuCategory(Base):
    __tablename__="menu_categories"

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