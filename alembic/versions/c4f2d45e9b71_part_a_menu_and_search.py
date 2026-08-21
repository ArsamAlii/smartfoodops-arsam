"""add Part A restaurant details and retrieval content chunks

Revision ID: c4f2d45e9b71
Revises: 60f1cd7092af
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f2d45e9b71"
down_revision = "60f1cd7092af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("restaurants", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("restaurants", sa.Column("operating_hours", sa.String(255), nullable=True))
    op.add_column("menu_items", sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("menu_items", "stock", existing_type=sa.Integer(), nullable=True)
    op.add_column("order_status_history", sa.Column("actor", sa.String(100), nullable=True))
    op.add_column("order_status_history", sa.Column("reason", sa.String(255), nullable=True))
    op.create_table(
        "refunds",
        sa.Column("refund_id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.payment_id"]),
        sa.PrimaryKeyConstraint("refund_id"),
        sa.UniqueConstraint("payment_id"),
    )
    op.create_table(
        "settlements",
        sa.Column("settlement_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("rider_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.order_id"]),
        sa.PrimaryKeyConstraint("settlement_id"),
        sa.UniqueConstraint("order_id"),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_active_order_per_rider ON orders (rider_id) "
        "WHERE rider_id IS NOT NULL AND status IN ('assigned', 'picked_up', 'delivered')"
    )
    op.create_table(
        "content_chunks",
        sa.Column("content_chunk_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.menu_item_id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.restaurant_id"]),
        sa.PrimaryKeyConstraint("content_chunk_id"),
    )
    op.create_index("ix_content_chunks_restaurant_id", "content_chunks", ["restaurant_id"])
    op.create_index("ix_content_chunks_menu_item_id", "content_chunks", ["menu_item_id"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_active_order_per_rider")
    op.drop_index("ix_content_chunks_menu_item_id", table_name="content_chunks")
    op.drop_index("ix_content_chunks_restaurant_id", table_name="content_chunks")
    op.drop_table("content_chunks")
    op.drop_table("settlements")
    op.drop_table("refunds")
    op.drop_column("order_status_history", "reason")
    op.drop_column("order_status_history", "actor")
    op.alter_column("menu_items", "stock", existing_type=sa.Integer(), nullable=False)
    op.drop_column("menu_items", "order_index")
    op.drop_column("restaurants", "operating_hours")
    op.drop_column("restaurants", "description")
