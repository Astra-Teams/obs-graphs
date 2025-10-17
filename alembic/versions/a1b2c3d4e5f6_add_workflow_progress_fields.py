"""add workflow progress tracking columns

Revision ID: a1b2c3d4e5f6
Revises: f2g3h4i5j6k7
Create Date: 2025-10-13 00:00:00.000001
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column("progress_message", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "workflows",
        sa.Column("progress_percent", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflows", "progress_percent")
    op.drop_column("workflows", "progress_message")
