"""Change prompt to JSON array

Revision ID: c5f6g7h8i9j0
Revises: b4d2e8f3c9a1
Create Date: 2025-10-13 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c5f6g7h8i9j0"
down_revision = "b4d2e8f3c9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Change prompt column from Text to JSON to support array of prompts.

    Migrates existing string prompts to single-element arrays.
    """
    # Create a new column with JSON type
    op.add_column("workflows", sa.Column("prompt_new", sa.JSON(), nullable=True))

    # Migrate existing data: wrap string prompts in arrays
    # Use raw SQL for compatibility with both SQLite and PostgreSQL
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE workflows
            SET prompt_new = CASE
                WHEN prompt IS NULL THEN NULL
                ELSE json_array(prompt)
            END
            """
        )
    )

    # Drop old column and rename new one
    op.drop_column("workflows", "prompt")
    op.alter_column("workflows", "prompt_new", new_column_name="prompt")


def downgrade() -> None:
    """
    Revert prompt column from JSON back to Text.

    Takes the first element from the array if it exists.
    """
    # Create a new column with Text type
    op.add_column("workflows", sa.Column("prompt_new", sa.Text(), nullable=True))

    # Migrate data back: extract first element from array
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE workflows
            SET prompt_new = CASE
                WHEN prompt IS NULL THEN NULL
                WHEN json_array_length(prompt) > 0 THEN json_extract(prompt, '$[0]')
                ELSE NULL
            END
            """
        )
    )

    # Drop JSON column and rename Text column
    op.drop_column("workflows", "prompt")
    op.alter_column("workflows", "prompt_new", new_column_name="prompt")
