"""Tests for the finding approval workflow."""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.run import Run
from app.models.finding import Finding
from app.models.audit_log import AuditLog
from app.workflow.graph import compile_workflow


@pytest.fixture
def db_session():
    """Provides a database session and cleans up after the test."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def temp_document():
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(f"Test document. Unique: {uuid.uuid4()}")
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_workflow_pauses_before_approval(client: TestClient, temp_document: str) -> None:
    """Test that creating a run pauses the workflow at the approval stage."""
    
    response = client.post("/api/v1/runs", json={"file_path": temp_document})
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    
    state_resp = client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp.status_code == 200
    state = state_resp.json()
    
    # The workflow should be paused before approval_node executes.
    # verify_node sets current_stage to "approval".
    assert state["current_stage"] == "approval"
    assert "verify" in state["completed_stages"]
    assert "approval" not in state["completed_stages"]


def test_approve_finding_single_success(client: TestClient, db_session) -> None:
    """Test approving a single finding."""
    # 1. Manually setup DB
    run = Run(status="pending", input_metadata={"file_path": "fake.txt"})
    db_session.add(run)
    db_session.commit()
    
    finding = Finding(
        run_id=run.id,
        title="Test finding",
        summary="Test summary",
        severity="low",
        payload={},
        status="pending"
    )
    db_session.add(finding)
    db_session.commit()
    
    # 2. Call approve API
    payload = {"decision": "approve", "comment": "Looks good"}
    resp = client.post(f"/api/v1/runs/{run.id}/findings/{finding.id}/approve", json=payload)
    
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["remaining_pending"] == 0
    
    # 3. Verify DB changes
    db_session.refresh(finding)
    assert finding.status == "approved"
    
    # 4. Verify audit log
    audit = db_session.query(AuditLog).filter_by(run_id=run.id).first()
    assert audit is not None
    assert audit.action == "finding_approve"
    assert audit.payload["comment"] == "Looks good"


def test_edit_finding_success(client: TestClient, db_session) -> None:
    """Test editing a finding preserves the original summary."""
    run = Run(status="pending", input_metadata={"file_path": "fake.txt"})
    db_session.add(run)
    db_session.commit()
    
    finding = Finding(
        run_id=run.id,
        title="Test",
        summary="Original AI text",
        severity="low",
        payload={},
        status="pending"
    )
    db_session.add(finding)
    db_session.commit()
    
    payload = {"decision": "edit", "edited_text": "Human corrected text"}
    resp = client.post(f"/api/v1/runs/{run.id}/findings/{finding.id}/approve", json=payload)
    
    assert resp.status_code == 200
    
    db_session.refresh(finding)
    assert finding.status == "approved"
    assert finding.summary == "Human corrected text"
    assert finding.payload["original_summary"] == "Original AI text"
    
    audit = db_session.query(AuditLog).filter_by(run_id=run.id).first()
    assert audit.action == "finding_edit"
    assert audit.payload["edited_text"] == "Human corrected text"


def test_reject_finding_success(client: TestClient, db_session) -> None:
    """Test rejecting a finding."""
    run = Run(status="pending", input_metadata={"file_path": "fake.txt"})
    db_session.add(run)
    db_session.commit()
    
    finding = Finding(
        run_id=run.id,
        title="Test",
        summary="Text",
        severity="low",
        payload={},
        status="pending"
    )
    db_session.add(finding)
    db_session.commit()
    
    payload = {"decision": "reject", "comment": "Invalid"}
    resp = client.post(f"/api/v1/runs/{run.id}/findings/{finding.id}/approve", json=payload)
    
    assert resp.status_code == 200
    
    db_session.refresh(finding)
    assert finding.status == "rejected"


def test_concurrent_approval_protection(client: TestClient, db_session) -> None:
    """Test that an already reviewed finding returns 409 Conflict."""
    run = Run(status="pending", input_metadata={"file_path": "fake.txt"})
    db_session.add(run)
    db_session.commit()
    
    finding = Finding(
        run_id=run.id,
        title="Test",
        summary="Text",
        severity="low",
        payload={},
        status="approved"  # Already approved
    )
    db_session.add(finding)
    db_session.commit()
    
    payload = {"decision": "approve"}
    resp = client.post(f"/api/v1/runs/{run.id}/findings/{finding.id}/approve", json=payload)
    
    assert resp.status_code == 409
    assert "already been reviewed" in resp.json()["detail"]


def test_security_wrong_run_id_rejected(client: TestClient, db_session) -> None:
    """Test that finding must belong to the specified run_id."""
    run = Run(status="pending", input_metadata={"file_path": "fake.txt"})
    db_session.add(run)
    db_session.commit()
    
    finding = Finding(
        run_id=run.id,
        title="Test",
        summary="Text",
        severity="low",
        payload={},
        status="pending"
    )
    db_session.add(finding)
    db_session.commit()
    
    fake_run_id = str(uuid.uuid4())
    payload = {"decision": "approve"}
    resp = client.post(f"/api/v1/runs/{fake_run_id}/findings/{finding.id}/approve", json=payload)
    
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_auto_resume_workflow_on_last_approval(client: TestClient, temp_document: str, db_session) -> None:
    """Test that the workflow resumes automatically when the last pending finding is reviewed."""
    # 1. Create run through API to get the workflow started
    response = client.post("/api/v1/runs", json={"file_path": temp_document})
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    
    # 2. Add two pending findings
    f1 = Finding(run_id=uuid.UUID(run_id), title="F1", summary="S1", severity="low", payload={}, status="pending")
    f2 = Finding(run_id=uuid.UUID(run_id), title="F2", summary="S2", severity="low", payload={}, status="pending")
    db_session.add_all([f1, f2])
    db_session.commit()
    
    # 3. Approve first finding - should NOT resume
    payload1 = {"decision": "approve"}
    r1 = client.post(f"/api/v1/runs/{run_id}/findings/{f1.id}/approve", json=payload1)
    assert r1.status_code == 200
    assert r1.json()["remaining_pending"] == 1
    
    state_resp1 = client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp1.json()["current_stage"] == "approval" # Still paused
    
    # 4. Reject second finding - SHOULD resume
    payload2 = {"decision": "reject"}
    r2 = client.post(f"/api/v1/runs/{run_id}/findings/{f2.id}/approve", json=payload2)
    assert r2.status_code == 200
    assert r2.json()["remaining_pending"] == 0
    
    # 5. Check if it resumed and completed
    state_resp2 = client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp2.json()["current_stage"] == "completed"
    assert "approval" in state_resp2.json()["completed_stages"]
