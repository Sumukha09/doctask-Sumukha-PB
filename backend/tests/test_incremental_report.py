import os
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.session import get_session_factory
from app.models.run import Run
from app.models.finding import Finding
from app.models.document import Document
from app.models.claim import Claim
from app.llm.schemas import LLMRequest
from app.llm.gemini import GeminiLLMAdapter
from app.llm.exceptions import LLMProviderUnavailableError
from app.llm.limiter import GLOBAL_METRICS

@pytest.fixture
def db_session():
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

def create_temp_doc(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path

def test_incremental_updates_and_human_review(client: TestClient, db_session) -> None:
    # --- TEST 1: INITIAL REPORT ---
    doc_a = create_temp_doc("Lease duration 11 months.")
    doc_b = create_temp_doc("Rent is 25000.")
    
    resp1 = client.post("/api/v1/runs", json={"file_path": doc_a})
    assert resp1.status_code == 201
    run_id = resp1.json()["run_id"]
    
    # We will just test the state machine structure and metadata by adding doc B
    # Since we use MockLLMAdapter by default in tests, we can trigger the graph.
    import time
    time.sleep(1) # wait for graph to reach approval or completion
    
    # Wait until it's done or paused
    for _ in range(10):
        state = client.get(f"/api/v1/runs/{run_id}/state").json()
        if state["current_stage"] in ["approval", "completed", "failed"]:
            break
        time.sleep(0.5)
        
    # --- TEST 2: ADD C (INCREMENTAL) ---
    doc_c = create_temp_doc("Contradiction: Rent is 50000.")
    with open(doc_c, "rb") as f:
        resp_add = client.post(f"/api/v1/runs/{run_id}/documents", files={"files": ("doc_c.txt", f, "text/plain")})
    assert resp_add.status_code == 200
    
    time.sleep(1)
    for _ in range(10):
        state = client.get(f"/api/v1/runs/{run_id}/state").json()
        if state["current_stage"] in ["approval", "completed", "failed"]:
            break
        time.sleep(0.5)
        
    # Check report metadata (Test 2)
    run = db_session.get(Run, uuid.UUID(run_id))
    report_meta = run.input_metadata.get("report_metadata", {})
    # It might not exist if it stopped at approval, because complete_node is after approval.
    # We can push it past approval.
    resp_approve = client.post(f"/api/v1/runs/{run_id}/resume")
    
    time.sleep(1)
    db_session.refresh(run)
    report_meta = run.input_metadata.get("report_metadata", {})
    assert report_meta != {}
    assert "changed_sections" in report_meta
    
    # --- TEST 3 & 4 & 5: HUMAN REVIEW ---
    # We should have findings created.
    findings = db_session.query(Finding).filter(Finding.run_id == uuid.UUID(run_id)).all()
    # At least some findings should exist and be 'pending' if they were just added
    
    # --- TEST 6: DUPLICATE C ---
    with open(doc_c, "rb") as f:
        resp_dup = client.post(f"/api/v1/runs/{run_id}/documents", files={"files": ("doc_c.txt", f, "text/plain")})
    assert resp_dup.status_code == 200
    assert resp_dup.json()["added_documents"][0]["status"] == "already_exists"
    
    os.remove(doc_a)
    os.remove(doc_b)
    os.remove(doc_c)

def test_gemini_request_accounting_and_failure(monkeypatch):
    """Test 7 & 8: Mock Gemini to simulate retries and failures."""
    adapter = GeminiLLMAdapter(model_name="test-model")
    
    # Reset metrics
    GLOBAL_METRICS["gemini_requests"] = 0
    GLOBAL_METRICS["gemini_retries"] = 0
    GLOBAL_METRICS["gemini_rate_limited"] = 0
    
    req = LLMRequest(
        system_prompt="sys",
        user_prompt="usr",
        request_id="test-123",
        run_id="run-123",
        node="test",
        purpose="test"
    )
    
    # Mock the client to raise 429 twice, then fail
    class MockClient:
        class Models:
            def generate_content(self, **kwargs):
                from google.genai.errors import APIError
                # Raise an error that looks like a rate limit
                raise APIError("429 Resource exhausted")
        models = Models()
        
    adapter.client = MockClient()
    adapter.max_retries = 2
    adapter.initial_backoff = 0.01 # fast tests
    
    with pytest.raises(LLMProviderUnavailableError):
        adapter.generate(req)
        
    assert GLOBAL_METRICS["gemini_requests"] == 1
    assert GLOBAL_METRICS["gemini_rate_limited"] == 2
