from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    generated_content_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.restaurant_id"),
        nullable=False,
        index=True,
    )

    menu_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("menu_items.menu_item_id"),
        nullable=True,
        index=True,
    )

    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    content: Mapped[dict | str] = mapped_column(
        JSON,
        nullable=False,
    )

    prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )