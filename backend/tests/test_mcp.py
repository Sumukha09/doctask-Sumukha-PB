"""Tests for the MCP server tools."""
import os
import uuid
from unittest.mock import patch

import pytest
from app.db.session import get_session_factory
from app.models.run import Run
from app.models.finding import Finding
from app.models.document import Document

# Force mock LLM provider for tests to avoid Gemini calls
os.environ["LLM_PROVIDER"] = "mock"

# Import tools after setting environ
from app.mcp.tools import register_tools

class MockMCP:
    def tool(self):
        def decorator(func):
            setattr(self, func.__name__, func)
            return func
        return decorator

mcp = MockMCP()
register_tools(mcp)

create_run = mcp.create_run
get_run = mcp.get_run
get_run_state = mcp.get_run_state
resume_run = mcp.resume_run
add_documents = mcp.add_documents
get_findings = mcp.get_findings
review_finding = mcp.review_finding
get_report = mcp.get_report

def test_mcp_create_run_and_get():
    """Test creating a run and fetching it."""
    # Mock threading so background task doesn't actually run during this simple test
    with patch("threading.Thread.start"):
        res = create_run(file_paths=["/fake/path.pdf"])
        assert "run_id" in res
        assert res["current_stage"] == "ingest"
        
        run_id = res["run_id"]
        
        # Test get_run
        get_res = get_run(run_id=run_id)
        assert get_res["run_id"] == run_id
        assert get_res["status"] == "running"
        
        # Test get_run_state
        state_res = get_run_state(run_id=run_id)
        assert state_res["run_id"] == run_id
        assert state_res["current_stage"] == "ingest"

def test_mcp_resume_run():
    """Test resuming a run."""
    with patch("threading.Thread.start"):
        res = create_run(file_paths=["/fake/path.pdf"])
        run_id = res["run_id"]
        
        # Manually fail the run in DB to test resume
        session_factory = get_session_factory()
        with session_factory() as session:
            run = session.get(Run, uuid.UUID(run_id))
            run.status = "failed"
            session.commit()
            
        resume_res = resume_run(run_id=run_id)
        assert resume_res["status"] == "resumed"

def test_mcp_add_documents(tmp_path):
    """Test adding documents incrementally."""
    with patch("threading.Thread.start"):
        res = create_run(file_paths=["/fake/path.pdf"])
        run_id = res["run_id"]
        
        fake_doc = tmp_path / "new_doc.pdf"
        fake_doc.write_text("fake content")
        
        add_res = add_documents(run_id=run_id, file_paths=[str(fake_doc)])
        assert len(add_res["added_documents"]) == 1
        assert add_res["added_documents"][0]["path"] == str(fake_doc)
        assert add_res["status"] == "running"

def test_mcp_review_finding():
    """Test finding review."""
    with patch("threading.Thread.start"):
        res = create_run(file_paths=["/fake/path.pdf"])
        run_id = res["run_id"]
        
        # Manually insert a finding
        session_factory = get_session_factory()
        with session_factory() as session:
            finding = Finding(
                run_id=uuid.UUID(run_id),
                title="Test finding",
                status="pending"
            )
            session.add(finding)
            session.commit()
            finding_id = str(finding.id)
            
        findings_res = get_findings(run_id=run_id)
        assert len(findings_res) == 1
        
        review_res = review_finding(run_id=run_id, finding_id=finding_id, decision="approve")
        assert review_res["status"] == "approved"

def test_mcp_get_report():
    """Test retrieving report."""
    with patch("threading.Thread.start"):
        res = create_run(file_paths=["/fake/path.pdf"])
        run_id = res["run_id"]
        
        # Manually set report metadata
        session_factory = get_session_factory()
        with session_factory() as session:
            run = session.get(Run, uuid.UUID(run_id))
            run.input_metadata = {"report_metadata": {"version": 1}}
            session.commit()
            
        report_res = get_report(run_id=run_id)
        assert report_res["status"] == "available"
        assert report_res["report_metadata"]["version"] == 1
