"""add Week 4 vector metadata to content chunks

Revision ID: d2af3ce486b4
Revises: ef63db14a168
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision: str = "d2af3ce486b4"
down_revision: Union[str, Sequence[str], None] = "ef63db14a168"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# OpenAI text-embedding-3-small uses 1536 dimensions.
# The real EmbeddingProvider must produce vectors of this size.
EMBEDDING_DIMENSION = 384


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Remove old restaurant-only chunks.
    #
    # Week 4 search is menu-item retrieval, and every searchable
    # chunk represents one actual menu item.
    # ---------------------------------------------------------
    op.execute(
        """
        DELETE FROM content_chunks
        WHERE menu_item_id IS NULL
        """
    )

    # ---------------------------------------------------------
    # 2. Add Week 4 metadata columns.
    #
    # Initially nullable so existing rows can be populated safely.
    # ---------------------------------------------------------
    op.add_column(
        "content_chunks",
        sa.Column(
            "cuisine",
            sa.String(100),
            nullable=True,
        ),
    )

    op.add_column(
        "content_chunks",
        sa.Column(
            "price",
            sa.Numeric(10, 2),
            nullable=True,
        ),
    )

    op.add_column(
        "content_chunks",
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=True,
        ),
    )

    op.add_column(
        "content_chunks",
        sa.Column(
            "text_hash",
            sa.String(64),
            nullable=True,
        ),
    )

    op.add_column(
        "content_chunks",
        sa.Column(
            "embedding",
            Vector(EMBEDDING_DIMENSION),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # 3. Populate metadata for existing menu-item chunks.
    # ---------------------------------------------------------
    op.execute(
        """
        UPDATE content_chunks AS cc
        SET
            cuisine = r.cuisine,
            price = mi.price,
            is_available = mi.is_available,
            text_hash = md5(cc.text)
        FROM menu_items AS mi
        JOIN menu_categories AS mc
            ON mc.category_id = mi.category_id
        JOIN restaurants AS r
            ON r.restaurant_id = mc.restaurant_id
        WHERE cc.menu_item_id = mi.menu_item_id
        """
    )

    # ---------------------------------------------------------
    # 4. Metadata is mandatory for searchable chunks.
    # ---------------------------------------------------------
    op.alter_column(
        "content_chunks",
        "cuisine",
        existing_type=sa.String(100),
        nullable=False,
    )

    op.alter_column(
        "content_chunks",
        "price",
        existing_type=sa.Numeric(10, 2),
        nullable=False,
    )

    op.alter_column(
        "content_chunks",
        "is_available",
        existing_type=sa.Boolean(),
        nullable=False,
    )

    op.alter_column(
        "content_chunks",
        "text_hash",
        existing_type=sa.String(64),
        nullable=False,
    )

    # ---------------------------------------------------------
    # 5. Index metadata used by retrieval filters.
    # ---------------------------------------------------------
    op.create_index(
        "ix_content_chunks_is_available",
        "content_chunks",
        ["is_available"],
    )

    op.create_index(
        "ix_content_chunks_cuisine",
        "content_chunks",
        ["cuisine"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_content_chunks_cuisine",
        table_name="content_chunks",
    )

    op.drop_index(
        "ix_content_chunks_is_available",
        table_name="content_chunks",
    )

    op.drop_column(
        "content_chunks",
        "embedding",
    )

    op.drop_column(
        "content_chunks",
        "text_hash",
    )

    op.drop_column(
        "content_chunks",
        "is_available",
    )

    op.drop_column(
        "content_chunks",
        "price",
    )

    op.drop_column(
        "content_chunks",
        "cuisine",
    )