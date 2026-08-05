from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    # -------------------------------------------------------
    # Primary Key
    # -------------------------------------------------------
    menu_item_id: Mapped[int] = mapped_column(primary_key=True)

    # -------------------------------------------------------
    # Foreign Key
    # -------------------------------------------------------
    category_id: Mapped[int] = mapped_column(
        ForeignKey("menu_categories.category_id"),
        nullable=False,
    )

    # -------------------------------------------------------
    # Basic Information
    # -------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(255),
    )

    image_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # -------------------------------------------------------
    # Pricing
    # -------------------------------------------------------
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    stock: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # -------------------------------------------------------
    # Audit Information
    # -------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -------------------------------------------------------
    # Relationships
    # -------------------------------------------------------
    category: Mapped["MenuCategory"] = relationship(
        back_populates="menu_items"
    )

    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="menu_item"
    )