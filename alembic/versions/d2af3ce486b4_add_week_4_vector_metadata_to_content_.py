"""add Week 4 vector metadata to content chunks

Revision ID: d2af3ce486b4
Revises: ef63db14a168
Create Date: 2026-08-25 15:13:18.021335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2af3ce486b4'
down_revision: Union[str, Sequence[str], None] = 'ef63db14a168'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
