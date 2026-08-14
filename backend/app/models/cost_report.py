"""ORM model: ``cost_reports``.

A run produces at most one cost report. Costs are tracked in micro-units of
the configured currency to avoid floating-point drift; the ``currency`` column
stores the ISO 4217 code. ``breakdown`` is JSONB so additional cost dimensions
can be added without a schema change.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.run import Run
from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CostReport(Base):
    """The aggregated cost of a single run."""

    __tablename__ = "cost_reports"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_cost_reports_run_id"),
        Index("ix_cost_reports_created_at", "created_at"),
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
    total_cost_micro: Mapped[int] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        doc="Total cost in micro-units of `currency`.",
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        server_default="USD",
    )
    breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped["Run"] = relationship(back_populates="cost_report")