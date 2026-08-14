"""Service for managing Audit Logs and Cost Reports."""

import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cost_report import CostReport


def create_audit_log(
    session: Session,
    run_id: uuid.UUID,
    action: str,
    details: dict | None = None,
) -> AuditLog:
    """Create an audit log entry for a run."""
    log = AuditLog(
        run_id=run_id,
        actor="system",
        action=action,
        payload=details or {},
    )
    session.add(log)
    session.commit()
    return log

def record_cost(
    session: Session,
    run_id: uuid.UUID,
    total_cost_micro: int,
    currency: str = "USD",
    breakdown: dict | None = None,
) -> CostReport:
    """Record LLM cost metrics for a step."""
    report = CostReport(
        run_id=run_id,
        total_cost_micro=total_cost_micro,
        currency=currency,
        breakdown=breakdown,
    )
    session.add(report)
    session.commit()
    return report
