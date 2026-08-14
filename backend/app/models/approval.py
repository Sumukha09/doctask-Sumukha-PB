"""ORM model: ``approvals``.

An approval is a human decision recorded against a run. Multiple approvals
can exist for the same run (one per reviewer, or one per artifact). The
``decision`` column records the choice (``approved``, ``rejected``, ...) and
``reviewer_id`` identifies the human or service that made the decision.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import Run
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Approval(Base):
    """A human approval recorded against a run."""

    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_run_id", "run_id"),
        Index("ix_approvals_decision", "decision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped["Run"] = relationship(back_populates="approvals")