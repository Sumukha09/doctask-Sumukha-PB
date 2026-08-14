"""Integration tests proving cross-layer interoperability for FlowDocs V2."""
from __future__ import annotations

import os
import tempfile
import uuid
import concurrent.futures

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.run import Run
from app.models.finding import Finding
from app.models.audit_log import AuditLog
from app.llm.mock import MockLLMAdapter
from app.services.extraction import create_finding


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
    """Provides a temporary file for testing."""
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(f"Integration test document. Unique: {uuid.uuid4()}")
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_end_to_end_happy_path(client: TestClient, temp_document: str, db_session) -> None:
    """Prove API -> Workflow -> LLM Mock -> Services -> Checkpoint -> Resume -> DB works."""
    
    # 1. API -> Workflow -> DB (Ingestion)
    response = client.post("/api/v1/runs", json={"file_path": temp_document})
    assert response.status_code == 201
    data = response.json()
    run_id = data["run_id"]
    
    # 2. Assert workflow paused at approval via checkpointer
    assert data["current_stage"] == "approval"
    
    # 3. Workflow -> LLM Mock -> Services (Simulating Extract & Analyze)
    # The current graph nodes are placeholders, so we simulate their internal LLM/DB logic manually here
    # to prove the layers can integrate correctly when the real nodes are implemented.
    from app.llm.schemas import LLMRequest
    from pydantic import BaseModel
    
    class MockFinding(BaseModel):
        title: str
        summary: str
        severity: str
        confidence: float
        
    class MockExtraction(BaseModel):
        findings: list[MockFinding]
        
    adapter = MockLLMAdapter()
    req = LLMRequest(
        system_prompt="Extract claims",
        user_prompt="The sky is blue.",
        response_schema=MockExtraction
    )
    
    # Simulate LLM extraction
    response = adapter.generate(req)
    assert response.parsed_content is not None
    assert len(response.parsed_content.findings) > 0
    mock_finding = response.parsed_content.findings[0]
    
    # Save the extracted finding using the service layer
    finding = create_finding(
        session=db_session,
        run_id=uuid.UUID(run_id),
        title=mock_finding.title,
        status="pending",
        summary=mock_finding.summary,
        severity=mock_finding.severity,
        payload={"confidence": mock_finding.confidence}
    )
    
    # 4. Findings -> Human Approval/Edit -> Finalization
    # Human edits the finding
    edit_payload = {
        "decision": "edit",
        "edited_text": "Human reviewed: The sky is blue."
    }
    approve_resp = client.post(f"/api/v1/runs/{run_id}/findings/{finding.id}/approve", json=edit_payload)
    assert approve_resp.status_code == 200
    
    # 5. Check state automatically resumed to completed
    state_resp = client.get(f"/api/v1/runs/{run_id}/state")
    assert state_resp.status_code == 200
    final_state = state_resp.json()
    assert final_state["current_stage"] == "completed"
    
    # 6. Verify DB consistency and audit trail
    db_session.refresh(finding)
    assert finding.status == "approved"
    assert finding.summary == "Human reviewed: The sky is blue."
    assert finding.payload["original_summary"] == mock_finding.summary
    
    audit = db_session.query(AuditLog).filter_by(run_id=uuid.UUID(run_id), action="finding_edit").first()
    assert audit is not None
    assert audit.payload["edited_text"] == "Human reviewed: The sky is blue."


def test_concurrent_workflow_execution_locking(client: TestClient, temp_document: str, db_session) -> None:
    """Prove Run locking protects against concurrent API requests for the same finding."""
    # Setup run and pending finding
    response = client.post("/api/v1/runs", json={"file_path": temp_document})
    run_id = response.json()["run_id"]
    
    finding = create_finding(
        session=db_session,
        run_id=uuid.UUID(run_id),
        title="Concurrent Test",
        status="pending",
        summary="Testing locks",
    )
    finding_id = str(finding.id)
    
    # Simulate two reviewers submitting a decision at the exact same time
    def submit_approval(decision: str):
        try:
            return client.post(
                f"/api/v1/runs/{run_id}/findings/{finding_id}/approve",
                json={"decision": decision}
            )
        except Exception as e:
            return e
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_approval, "approve")
        f2 = executor.submit(submit_approval, "reject")
        
        results = [f1.result(), f2.result()]
        
    status_codes = [r.status_code for r in results if hasattr(r, "status_code")]
    
    # Exactly one request must succeed (200), and the other must be rejected as Conflict (409)
    assert 200 in status_codes
    assert 409 in status_codes
    
    # Verify DB has only 1 audit log to ensure the second request didn't partially commit
    audit_count = db_session.query(AuditLog).filter_by(run_id=uuid.UUID(run_id)).count()
    assert audit_count == 1


def test_errors_propagate_correctly_across_layers(client: TestClient, temp_document: str, db_session) -> None:
    """Prove errors propagate safely from deep layers up to the API."""
    # Trigger ingest error by providing an invalid path
    response = client.post("/api/v1/runs", json={"file_path": "/invalid/path.txt"})
    assert response.status_code == 201
    
    data = response.json()
    
    # Check that the error bubbled up cleanly to the workflow state
    assert "errors" in data
    assert any("File not found" in e for e in data["errors"])
    
    # Verify the workflow didn't crash but halted safely in the approval stage
    assert data["current_stage"] == "approval"
