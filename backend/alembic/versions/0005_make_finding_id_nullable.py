"""Make finding_id nullable

Revision ID: 0005_make_finding_id_nullable
Revises: 0004_rename_checkpoints

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_make_finding_id_nullable"
down_revision: Union[str, None] = "0004_rename_checkpoints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('claims', 'finding_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    op.alter_column('claims', 'finding_id',
               existing_type=sa.UUID(),
               nullable=False)
