"""FastAPI dependencies."""
from __future__ import annotations

from typing import Generator

from fastapi import Depends
from langgraph.checkpoint.postgres import PostgresSaver

from app.config import Settings
from app.db.session import get_session_factory


def get_db_session() -> Generator:
    """Yield a database session and clean it up automatically."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def get_checkpointer() -> Generator[PostgresSaver, None, None]:
    """Yield a configured PostgresSaver for LangGraph checkpoints."""
    settings = Settings()
    # PostgresSaver requires psycopg scheme, not psycopg+sqlalchemy
    conn_string = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    
    with PostgresSaver.from_conn_string(conn_string) as saver:
        saver.setup()
        yield saver
