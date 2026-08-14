"""ORM model: ``runs``.

A run is the top-level unit of work. Each run produces documents, findings,
claims, approvals, a cost report, and an audit trail. Deleting a run cascades
through all dependent tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.finding import Finding
    from app.models.approval import Approval
    from app.models.checkpoint import Checkpoint
    from app.models.cost_report import CostReport
    from app.models.audit_log import AuditLog

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Run(Base):
    """A single execution of the FlowDocs pipeline."""

    __tablename__ = "runs"
    __table_args__ = (
        Index("ix_runs_status", "status"),
        Index("ix_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    input_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Free-form JSON describing the inputs to the run.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    findings: Mapped[list["Finding"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    checkpoints: Mapped[list["Checkpoint"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    cost_report: Mapped["CostReport | None"] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )