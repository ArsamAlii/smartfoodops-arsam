from datetime import datetime
from sqlalchemy import DateTime,String #sql datatypes
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class User(Base):#user is a table in postgresql(creates a database model)
    __tablename__="users"

    user_id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    email: Mapped[str]= mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


    restaurants: Mapped[list["Restaurant"]] = relationship(
    back_populates="owner"
    )

#all orders of the custumer
    customer_orders: Mapped[list["Order"]] = relationship(
    back_populates="customer",
    foreign_keys="Order.customer_id"
    )


#all orders assigned to the rider
    assigned_orders: Mapped[list["Order"]] = relationship(
    back_populates="rider",
    foreign_keys="Order.rider_id"
    )