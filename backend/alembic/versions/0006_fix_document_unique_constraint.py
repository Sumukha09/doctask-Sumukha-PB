"""Deleted migration

Revision ID: 0006_fix_document_unique_constraint
Revises: 0005_make_finding_id_nullable

"""
from __future__ import annotations
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006_fix_document_unique_constraint"
down_revision: Union[str, None] = "0005_make_finding_id_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
