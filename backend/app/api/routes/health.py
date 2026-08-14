"""Health check endpoint.

The endpoint performs a real database query so a green response proves that
the backend can reach PostgreSQL through the configured pool.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health payload returned to clients."""

    status: str
    database: str


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe that verifies database connectivity.",
)
def health(session: Session = Depends(get_session)) -> HealthResponse:
    """Verify the application is alive and PostgreSQL is reachable.

    The route does one thing: open a session (provided by the dependency) and
    execute a trivial query. Any failure surfaces as a 500 from FastAPI's
    default exception handling, which is the correct signal for an unhealthy
    instance.
    """
    session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", database="ok")
