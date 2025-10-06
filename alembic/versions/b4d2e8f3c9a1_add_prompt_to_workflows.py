"""Add prompt to workflows

Revision ID: b4d2e8f3c9a1
Revises: a3c1ff94f1d5
Create Date: 2025-10-06 21:24:46.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b4d2e8f3c9a1"
down_revision = "a3c1ff94f1d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add prompt column to workflows table
    op.add_column("workflows", sa.Column("prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove prompt column from workflows table
    op.drop_column("workflows", "prompt")
