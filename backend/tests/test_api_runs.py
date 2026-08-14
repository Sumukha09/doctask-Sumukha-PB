"""Tests for the runs API endpoints."""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.run import Run


@pytest.fixture
def temp_document():
    """Provides a temporary file for ingestion testing."""
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(f"This is a test document with some content. Unique: {uuid.uuid4()}")
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_create_run_endpoint(client: TestClient, temp_document: str) -> None:
    """Test POST /api/v1/runs creates a run and invokes the workflow."""
    
    payload = {"file_path": temp_document}
    
    response = client.post("/api/v1/runs", json=payload)
    
    assert response.status_code == 201, response.text
    data = response.json()
    
    assert "run_id" in data
    assert "current_stage" in data
    assert "status" in data
    
    # The graph is now configured to halt at the human approval stage
    assert data["current_stage"] == "approval"
    assert "verify" in data.get("completed_stages", [])


def test_create_run_invalid_path_fails(client: TestClient) -> None:
    """Test POST /api/v1/runs gracefully handles missing files."""
    
    payload = {"file_path": "/fake/path/does_not_exist.txt"}
    
    response = client.post("/api/v1/runs", json=payload)
    
    assert response.status_code == 201, response.text
    data = response.json()
    
    # The ingest node fails and appends an error, but the workflow halts before approval
    assert data["current_stage"] == "approval"
    assert "errors" in data
    assert any("File not found" in err for err in data["errors"])


def test_get_run_status_endpoint(client: TestClient, temp_document: str) -> None:
    """Test GET /api/v1/runs/{run_id} returns basic run info."""
    
    # 1. Create a run via the API
    create_resp = client.post("/api/v1/runs", json={"file_path": temp_document})
    assert create_resp.status_code == 201
    run_id = create_resp.json()["run_id"]
    
    # 2. Fetch the run
    get_resp = client.get(f"/api/v1/runs/{run_id}")
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    
    assert data["id"] == run_id
    assert data["status"] == "pending"  # Initial state in DB


def test_get_run_state_endpoint(client: TestClient, temp_document: str) -> None:
    """Test GET /api/v1/runs/{run_id}/state returns durable LangGraph state."""
    
    # 1. Create a run via the API
    create_resp = client.post("/api/v1/runs", json={"file_path": temp_document})
    assert create_resp.status_code == 201
    run_id = create_resp.json()["run_id"]
    
    # 2. Fetch the state from the checkpointer
    state_resp = client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp.status_code == 200, state_resp.text
    data = state_resp.json()
    
    assert data["run_id"] == run_id
    assert data["current_stage"] == "approval"
    assert "verify" in data.get("completed_stages", [])


def test_get_run_status_not_found(client: TestClient) -> None:
    """Test GET /api/v1/runs/{run_id} handles missing runs."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/runs/{fake_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_get_run_state_not_found(client: TestClient) -> None:
    """Test GET /api/v1/runs/{run_id}/state handles missing states."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/runs/{fake_id}/state")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
