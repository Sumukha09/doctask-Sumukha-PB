"""ORM model: ``findings``.

A finding is the unit of insight produced for a run. Findings may assert
specific claims and reference supporting evidence from document chunks.
``payload`` is a free-form JSONB column so future workflow steps can attach
arbitrary fields without further migrations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.claim import Claim
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Finding(Base):
    """A single finding produced during a run."""

    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_run_id", "run_id"),
        Index("ix_findings_status", "status"),
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
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped["Run"] = relationship(back_populates="findings")
    claims: Mapped[list["Claim"]] = relationship(
        back_populates="finding",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )