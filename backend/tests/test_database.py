"""Database connectivity tests.

These tests connect to the real PostgreSQL container. They do not mock the
engine or the session layer.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_engine, get_session_factory


def test_engine_can_connect() -> None:
    """The SQLAlchemy engine completes a trivial round-trip."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()
    assert result == 1


def test_session_factory_returns_a_working_session() -> None:
    """`sessionmaker` produces a session that can execute queries."""
    session_factory = get_session_factory()
    session: Session = session_factory()
    try:
        result = session.execute(text("SELECT 1")).scalar_one()
        assert result == 1
    finally:
        session.close()


def test_pgvector_extension_is_present() -> None:
    """The initial migration has enabled the pgvector extension."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).fetchone()
    assert row is not None, "pgvector extension is not installed"
    assert row[0] == "vector"


def test_alembic_version_table_is_managed() -> None:
    """Alembic has stamped the current head revision."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).fetchone()
    assert row is not None, "alembic_version table is empty"
    assert row[0] == "0004_rename_checkpoints"
