"""Smoke tests for the health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    """`GET /health` returns 200 with `status` and `database` indicators."""
    response = client.get("/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"status": "ok", "database": "ok"}


def test_health_endpoint_is_exposed(client: TestClient) -> None:
    """The OpenAPI schema lists the health endpoint."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/health" in paths
