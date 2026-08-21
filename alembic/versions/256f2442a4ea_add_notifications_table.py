"""add notifications table

Revision ID: 256f2442a4ea
Revises: c4f2d45e9b71
Create Date: 2026-08-21 11:02:08.248184
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "256f2442a4ea"
down_revision: Union[str, Sequence[str], None] = "c4f2d45e9b71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "notification_id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "recipient_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "recipient_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "notification_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "message",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_notifications_recipient_id",
        "notifications",
        ["recipient_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_recipient_id",
        table_name="notifications",
    )
    op.drop_table("notifications")