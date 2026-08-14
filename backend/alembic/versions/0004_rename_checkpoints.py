"""Rename checkpoints to run_checkpoints

Revision ID: 0004_rename_checkpoints
Revises: 0003_confidence_check


"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0004_rename_checkpoints"
down_revision: Union[str, None] = "0003_confidence_check"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the table from checkpoints to run_checkpoints
    op.rename_table("checkpoints", "run_checkpoints")
    # Rename indexes to match new table name convention
    op.execute("ALTER INDEX ix_checkpoints_run_id RENAME TO ix_run_checkpoints_run_id")
    op.execute("ALTER INDEX ix_checkpoints_run_step RENAME TO ix_run_checkpoints_run_step")


def downgrade() -> None:
    # Revert index renames
    op.execute("ALTER INDEX ix_run_checkpoints_run_step RENAME TO ix_checkpoints_run_step")
    op.execute("ALTER INDEX ix_run_checkpoints_run_id RENAME TO ix_checkpoints_run_id")
    # Revert table rename
    op.rename_table("run_checkpoints", "checkpoints")
