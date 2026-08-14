"""Tests for the real document ingestion node (Step 5)."""
from __future__ import annotations

import hashlib
import os
import tempfile
import uuid

import pytest

from app.db.session import get_session_factory
from app.models import Document, Run
from app.workflow.graph import ingest_node, NODE_EXTRACT, NODE_INGEST
from app.workflow.state import WorkflowState


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
    """Provides a temporary file for ingestion testing."""
    fd, f_path = tempfile.mkstemp(suffix=".txt", text=True)
    content = f"This is a test document with some content. Unique ID: {uuid.uuid4()}"
    with os.fdopen(fd, "w") as f:
        f.write(content)
    
    yield f_path, content.encode("utf-8")
    
    if os.path.exists(f_path):
        os.remove(f_path)


def test_ingest_node_valid_document_success(db_session, temp_document) -> None:
    file_path, content = temp_document
    
    # 1. Create a Run in the DB
    run = Run(status="pending", input_metadata={"file_path": file_path})
    db_session.add(run)
    db_session.commit()
    
    # 2. Setup initial state
    state: WorkflowState = {
        "run_id": str(run.id),
        "current_stage": NODE_INGEST,
        "completed_stages": [],
    }
    
    # 3. Call the node
    result = ingest_node(state)
    
    # 4. Verify state transitions
    assert result.get("current_stage") == NODE_EXTRACT
    assert NODE_INGEST in result.get("completed_stages", [])
    
    # 5. Verify Document is created in DB and metadata captured
    db_session.commit()
    docs = db_session.query(Document).filter_by(run_id=run.id).all()
    assert len(docs) == 1
    doc = docs[0]
    
    # Verify hash
    expected_hash = hashlib.sha256(content).hexdigest()
    assert doc.hash == expected_hash
    assert doc.byte_size == len(content)
    assert doc.name == os.path.basename(file_path)
    assert doc.metadata_json == {"source": file_path}
    
    # Verify returned state includes the document ID
    assert result.get("document_ids") == [str(doc.id)]
    assert result.get("ingested_document_ids") == [str(doc.id)]

def test_ingest_node_missing_run_id_fails() -> None:
    state: WorkflowState = {"current_stage": NODE_INGEST}
    result = ingest_node(state)
    assert result.get("current_stage") == "failed"
    assert result.get("status") == "failed"
    assert "Missing run_id" in result.get("errors", [])[0]

def test_ingest_node_invalid_run_id_format_fails() -> None:
    state: WorkflowState = {"run_id": "not-a-uuid", "current_stage": NODE_INGEST}
    result = ingest_node(state)
    assert result.get("current_stage") == "failed"
    assert "Invalid run_id format" in result.get("errors", [])[0]

def test_ingest_node_run_not_found_fails(db_session) -> None:
    random_id = str(uuid.uuid4())
    state: WorkflowState = {"run_id": random_id, "current_stage": NODE_INGEST}
    result = ingest_node(state)
    assert result.get("current_stage") == "failed"
    assert "Run not found" in result.get("errors", [])[0]

def test_ingest_node_missing_file_path_fails(db_session) -> None:
    run = Run(status="pending", input_metadata={})
    db_session.add(run)
    db_session.commit()
    
    state: WorkflowState = {"run_id": str(run.id), "current_stage": NODE_INGEST}
    result = ingest_node(state)
    assert result.get("current_stage") == "failed"
    assert "Missing file_path" in result.get("errors", [])[0]

def test_ingest_node_file_not_found_fails(db_session) -> None:
    run = Run(status="pending", input_metadata={"file_path": "/path/does/not/exist.txt"})
    db_session.add(run)
    db_session.commit()
    
    state: WorkflowState = {"run_id": str(run.id), "current_stage": NODE_INGEST}
    result = ingest_node(state)
    assert result.get("current_stage") == "failed"
    assert "File not found" in result.get("errors", [])[0]

def test_ingest_node_duplicate_hash_handled(db_session, temp_document) -> None:
    file_path, content = temp_document
    
    # Create first run
    run1 = Run(status="pending", input_metadata={"file_path": file_path})
    db_session.add(run1)
    db_session.commit()
    
    state1: WorkflowState = {"run_id": str(run1.id), "current_stage": NODE_INGEST}
    result1 = ingest_node(state1)
    assert result1.get("current_stage") == NODE_EXTRACT
    
    # Create second run mapping to the same file (same hash)
    run2 = Run(status="pending", input_metadata={"file_path": file_path})
    db_session.add(run2)
    db_session.commit()
    
    state2: WorkflowState = {"run_id": str(run2.id), "current_stage": NODE_INGEST}
    result2 = ingest_node(state2)
    
    # Should succeed and use existing document
    assert result2.get("current_stage") == NODE_EXTRACT
    assert result2.get("document_ids") == result1.get("document_ids")
    
    # Verify only one Document exists in DB with this hash
    expected_hash = hashlib.sha256(content).hexdigest()
    docs = db_session.query(Document).filter_by(hash=expected_hash).all()
    assert len(docs) == 1
