"""add payment status

Revision ID: a3266096212e
Revises: fa949b3c05b1
Create Date: 2026-08-10 13:19:11.390642

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3266096212e"
down_revision: Union[str, Sequence[str], None] = "fa949b3c05b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # -------------------------------------------------------
    # Order Items
    # -------------------------------------------------------
    # Add the new column temporarily as nullable so existing
    # rows can be populated safely.
    op.add_column(
        "order_items",
        sa.Column(
            "unit_price",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )

    # Copy existing prices into the new column.
    op.execute(
        "UPDATE order_items "
        "SET unit_price = item_price "
        "WHERE unit_price IS NULL"
    )

    # Make the new column required.
    op.alter_column(
        "order_items",
        "unit_price",
        nullable=False,
    )

    # Remove the old column after the data has been copied.
    op.drop_column(
        "order_items",
        "item_price",
    )

    # -------------------------------------------------------
    # Payments
    # -------------------------------------------------------
    # Add payment status temporarily as nullable.
    op.add_column(
        "payments",
        sa.Column(
            "payment_status",
            sa.String(length=30),
            nullable=True,
        ),
    )

    # Give existing payments an initial status.
    op.execute(
        "UPDATE payments "
        "SET payment_status = 'pending' "
        "WHERE payment_status IS NULL"
    )

    # Make the new column required.
    op.alter_column(
        "payments",
        "payment_status",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # -------------------------------------------------------
    # Payments
    # -------------------------------------------------------
    op.drop_column(
        "payments",
        "payment_status",
    )

    # -------------------------------------------------------
    # Order Items
    # -------------------------------------------------------
    # Restore item_price and preserve the existing values.
    op.add_column(
        "order_items",
        sa.Column(
            "item_price",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE order_items "
        "SET item_price = unit_price "
        "WHERE item_price IS NULL"
    )

    op.alter_column(
        "order_items",
        "item_price",
        nullable=False,
    )

    op.drop_column(
        "order_items",
        "unit_price",
    )