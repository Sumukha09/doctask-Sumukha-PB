"""Shared pytest fixtures.

Tests run against the real PostgreSQL container launched by docker-compose.
They do not mock the database or any external service.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Ensure the application is configured to talk to the test database before any
# `app.*` is imported. These defaults match the docker-compose service.
os.environ.setdefault("POSTGRES_HOST", os.getenv("POSTGRES_HOST", "localhost"))
os.environ.setdefault("POSTGRES_PORT", os.getenv("POSTGRES_PORT", "5432"))
os.environ.setdefault("POSTGRES_DB", os.getenv("POSTGRES_DB", "flowdocs"))
os.environ.setdefault("POSTGRES_USER", os.getenv("POSTGRES_USER", "flowdocs"))


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Return a FastAPI test client backed by the real database."""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
