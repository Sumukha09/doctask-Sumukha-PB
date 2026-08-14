"""Service for managing Claim Evidence."""

import uuid

from sqlalchemy.orm import Session

from app.models.claim_evidence import ClaimEvidence


def add_evidence(
    session: Session,
    claim_id: uuid.UUID,
    chunk_id: uuid.UUID,
    relevance: float | None = None,
    snippet: str | None = None,
) -> ClaimEvidence:
    """Add a chunk of evidence supporting a claim."""
    evidence = ClaimEvidence(
        claim_id=claim_id,
        chunk_id=chunk_id,
        relevance=relevance,
        snippet=snippet,
    )
    session.add(evidence)
    session.commit()
    return evidence
