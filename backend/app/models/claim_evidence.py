"""ORM model: ``claim_evidence``.

Junction table linking a ``Claim`` to the ``DocumentChunk`` instances that
support it. The composite uniqueness constraint prevents the same chunk from
being attached twice to the same claim.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.document_chunk import DocumentChunk

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ClaimEvidence(Base):
    """An explicit link between a claim and a supporting document chunk."""

    __tablename__ = "claim_evidence"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "chunk_id",
            name="uq_claim_evidence_claim_chunk",
        ),
        CheckConstraint(
            "relevance IS NULL OR (relevance >= 0 AND relevance <= 1)",
            name="ck_claim_evidence_relevance_range",
        ),
        Index("ix_claim_evidence_claim_id", "claim_id"),
        Index("ix_claim_evidence_chunk_id", "chunk_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    relevance: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        doc="Relevance score in [0.0, 1.0].",
    )
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    claim: Mapped["Claim"] = relationship(back_populates="evidence")
    chunk: Mapped["DocumentChunk"] = relationship()