"""Database engine and session factory.

This module is the only place that knows how to construct a SQLAlchemy engine.
Routes and services obtain sessions through the :func:`get_session` dependency
so that the engine lifecycle is owned by the application.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _build_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        future=True,
    )


def get_engine() -> Engine:
    """Return the cached SQLAlchemy engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the cached session factory, creating it on first use."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )
    return _SessionLocal


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
