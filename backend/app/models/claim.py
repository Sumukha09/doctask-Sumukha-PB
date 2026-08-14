"""ORM model: ``claims``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.claim_evidence import ClaimEvidence
    from app.models.finding import Finding
    from app.models.run import Run


class Claim(Base):
    """A single claim belonging to a finding."""

    __tablename__ = "claims"
    __table_args__ = (
        Index("ix_claims_finding_id", "finding_id"),
        Index("ix_claims_run_id", "run_id"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_claims_confidence_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        doc="Denormalised for fast run-scoped queries.",
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        doc="Confidence score in [0.0, 1.0].",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finding: Mapped["Finding"] = relationship(back_populates="claims")
    run: Mapped["Run"] = relationship()
    evidence: Mapped[list["ClaimEvidence"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )