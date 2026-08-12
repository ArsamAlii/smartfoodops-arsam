"""add rider availability

Revision ID: bd0786bd9325
Revises: 48450fc0ed8a
Create Date: 2026-08-12 22:45:53.185766

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision: str = "bd0786bd9325"
down_revision: Union[str, Sequence[str], None] = "48450fc0ed8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_available")