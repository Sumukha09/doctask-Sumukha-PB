"""Service for managing Workflow Runs."""

import uuid

from sqlalchemy.orm import Session

from app.models.run import Run


def get_run(session: Session, run_id: uuid.UUID) -> Run | None:
    """Retrieve a run by its ID."""
    return session.get(Run, run_id)

def update_run_status(session: Session, run_id: uuid.UUID, status: str) -> Run:
    """Update the status of an existing run."""
    run = session.get(Run, run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found.")
    run.status = status
    session.commit()
    return run
