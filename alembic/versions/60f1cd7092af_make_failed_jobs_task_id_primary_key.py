"""make failed jobs task id primary key

Revision ID: 60f1cd7092af
Revises: a5565011bf7a
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "60f1cd7092af"
down_revision: Union[str, Sequence[str], None] = "a5565011bf7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_primary_key(
        "pk_failed_jobs",
        "failed_jobs",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "pk_failed_jobs",
        "failed_jobs",
        type_="primary",
    )