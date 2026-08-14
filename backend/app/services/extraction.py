import uuid

from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.claim import Claim


def create_finding(
    session: Session,
    run_id: uuid.UUID,
    title: str,
    status: str = "pending",
    summary: str | None = None,
    severity: str | None = None,
    payload: dict | None = None,
) -> Finding:
    """Create a new finding extracted from a document chunk."""
    finding = Finding(
        run_id=run_id,
        title=title,
        status=status,
        summary=summary,
        severity=severity,
        payload=payload,
    )
    session.add(finding)
    session.commit()
    return finding

def create_claim(
    session: Session,
    run_id: uuid.UUID,
    finding_id: uuid.UUID,
    statement: str,
    confidence: float | None = None,
) -> Claim:
    """Create a new normalized claim derived from a finding."""
    claim = Claim(
        run_id=run_id,
        finding_id=finding_id,
        statement=statement,
        confidence=confidence,
    )
    session.add(claim)
    session.commit()
    return claim
