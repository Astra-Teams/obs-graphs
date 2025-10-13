"""Add workflow_type column

Revision ID: d6g7h8i9j0k1
Revises: c5f6g7h8i9j0
Create Date: 2025-10-13 01:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d6g7h8i9j0k1"
down_revision = "c5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add workflow_type column to workflows table."""
    # Add workflow_type column with default value
    op.add_column(
        "workflows",
        sa.Column(
            "workflow_type",
            sa.String(50),
            nullable=False,
            server_default="article-proposal",
        ),
    )

    # Create index for workflow_type
    op.create_index(
        "ix_workflows_workflow_type", "workflows", ["workflow_type"], unique=False
    )


def downgrade() -> None:
    """Remove workflow_type column from workflows table."""
    # Drop index
    op.drop_index("ix_workflows_workflow_type", table_name="workflows")

    # Drop column
    op.drop_column("workflows", "workflow_type")
