"""Tests for incremental document upload and idempotent workflow processing."""
import uuid
import os
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.llm.mock import MockLLMAdapter

def test_incremental_upload_with_mock_spy(client: TestClient):
    original_generate = MockLLMAdapter.generate
    
    generate_calls = []
    
    def spy_generate(self, req):
        generate_calls.append(req)
        return original_generate(self, req)
        
    with patch.object(MockLLMAdapter, 'generate', new=spy_generate):
        # 1. Start run with Doc A
        b64_a = base64.b64encode(b"Content A").decode('utf-8')
        resp_a = client.post("/api/v1/runs", json={
            "files": [{"file_name": "docA.txt", "file_content_base64": b64_a}],
            "compliance_rules": "None"
        })
        assert resp_a.status_code == 201
        run_id = resp_a.json()["run_id"]
        
        calls_for_a = len(generate_calls)
        assert calls_for_a > 0
        generate_calls.clear() # Reset for next phase
        
        # 2. Add Doc B incrementally
        files_b = [("files", ("docB.txt", b"Content B", "text/plain"))]
        resp_b = client.post(f"/api/v1/runs/{run_id}/documents", files=files_b)
        assert resp_b.status_code == 201
        assert resp_b.json()["added_documents"][0]["filename"] == "docB.txt"
        
        calls_for_b = len(generate_calls)
        assert calls_for_b > 0 # Should process B
        generate_calls.clear()
        
        # 3. Add Doc B AGAIN (Duplicate)
        files_b_dup = [("files", ("docB.txt", b"Content B", "text/plain"))]
        resp_b_dup = client.post(f"/api/v1/runs/{run_id}/documents", files=files_b_dup)
        assert resp_b_dup.status_code == 201
        assert resp_b_dup.json()["added_documents"][0]["status"] == "already_exists"
        
        calls_for_dup = len(generate_calls)
        assert calls_for_dup == 0 # MUST BE 0 due to idempotency!
        
        # 4. Check details
        details = client.get(f"/api/v1/runs/{run_id}/details")
        assert details.status_code == 200
        data = details.json()
        assert len(data["documents"]) == 2
        doc_names = [d["name"] for d in data["documents"]]
        assert "docA.txt" in doc_names
        assert "docB.txt" in doc_names
        
def test_missing_run_returns_404(client: TestClient):
    files = [("files", ("test.txt", b"Content", "text/plain"))]
    fake_id = str(uuid.uuid4())
    resp = client.post(f"/api/v1/runs/{fake_id}/documents", files=files)
    assert resp.status_code == 404

def test_invalid_file_returns_400(client: TestClient):
    b64_a = base64.b64encode(b"Content A").decode('utf-8')
    resp_a = client.post("/api/v1/runs", json={
        "files": [{"file_name": "docA.txt", "file_content_base64": b64_a}],
        "compliance_rules": "None"
    })
    run_id = resp_a.json()["run_id"]
    
    # Empty file
    files = [("files", ("empty.txt", b"", "text/plain"))]
    resp = client.post(f"/api/v1/runs/{run_id}/documents", files=files)
    assert resp.status_code == 400
