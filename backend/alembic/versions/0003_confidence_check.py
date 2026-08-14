"""Add a range CHECK constraint on ``claims.confidence``.

This is the only schema change requested in the post-Step-2 audit. The
``Numeric(5, 4)`` column has always been declared as a probability in
[0.0, 1.0]; the equivalent CHECK ``ck_claim_evidence_relevance_range``
already exists on the symmetric ``claim_evidence.relevance`` column. This
migration brings the two into parity.

Revision ID: 0003_claims_confidence_range_check
Revises: 0002_domain_schema
Create Date: 2026-08-11

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_confidence_check"
down_revision: Union[str, None] = "0002_domain_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Constrain ``claims.confidence`` to the unit interval [0.0, 1.0]."""
    op.create_check_constraint(
        "ck_claims_confidence_range",
        "claims",
        "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
    )


def downgrade() -> None:
    """Remove the range CHECK constraint."""
    op.drop_constraint("ck_claims_confidence_range", "claims", type_="check")
