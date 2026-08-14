"""SQLAlchemy declarative base for all ORM models.

Keep this module minimal: it defines the single shared declarative base.
Domain models are added in later steps.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Project-wide declarative base class."""

    pass
