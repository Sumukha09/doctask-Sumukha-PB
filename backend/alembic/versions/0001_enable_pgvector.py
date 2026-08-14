"""Step 1 — foundation: enable the pgvector extension.

This is the only migration for Step 1. Application tables are added in later
steps; once they exist, Alembic autogeneration will produce the schema diffs
from the SQLAlchemy metadata.

Revision ID: 0001_enable_pgvector
Revises:

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_enable_pgvector"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable the pgvector extension.

    ``CREATE EXTENSION`` is idempotent because Alembic wraps it in a
    transaction block; the ``IF NOT EXISTS`` clause makes the statement safe
    to re-run on partially-migrated databases.
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Drop the pgvector extension.

    This is provided for completeness. Dropping the extension will fail if any
    column depends on it; that is the correct behaviour.
    """
    op.execute("DROP EXTENSION IF EXISTS vector")
