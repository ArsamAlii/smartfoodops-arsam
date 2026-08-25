from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from app.db.base import Base


class ContentChunk(Base):
    """
    Search-ready representation of a menu item.

    Each menu item gets one enriched chunk containing enough
    restaurant and menu context for semantic retrieval.
    """

    __tablename__ = "content_chunks"

    # ---------------------------------------------------------
    # Primary key
    # ---------------------------------------------------------
    content_chunk_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # ---------------------------------------------------------
    # Source references
    # ---------------------------------------------------------
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.restaurant_id"),
        nullable=False,
        index=True,
    )

    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.menu_item_id"),
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------
    # Menu metadata
    # ---------------------------------------------------------
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    cuisine: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )

    # ---------------------------------------------------------
    # Chunk information
    # ---------------------------------------------------------
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # SHA-256 hash of the embedding input text.
    # Used to avoid unnecessary re-embedding later.
    text_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # ---------------------------------------------------------
    # Vector embedding
    # ---------------------------------------------------------
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(384),
        nullable=True,
    )

    # ---------------------------------------------------------
    # Audit information
    # ---------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )