"""Tests for the service layer."""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.session import get_session_factory
from app.models import Document, Run, DocumentChunk, Finding, Claim, ClaimEvidence
from app.services.audit import create_audit_log, record_cost
from app.services.chunk import create_chunks, get_chunk
from app.services.document import get_document, get_or_create_document
from app.services.extraction import create_claim, create_finding
from app.services.run import get_run, update_run_status
from app.services.verification import add_evidence


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
    """Creates a temporary file and returns its path."""
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(f"This is a test document with some content. Unique: {uuid.uuid4()}")
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_run_service(db_session):
    # Setup
    run = Run(status="pending")
    db_session.add(run)
    db_session.commit()
    
    # Test get_run
    fetched = get_run(db_session, run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.status == "pending"
    
    # Test missing run
    assert get_run(db_session, uuid.uuid4()) is None
    
    # Test update status
    updated = update_run_status(db_session, run.id, "running")
    assert updated.status == "running"
    
    db_session.refresh(run)
    assert run.status == "running"


def test_document_service_get_or_create(db_session, temp_document):
    run = Run(status="running")
    db_session.add(run)
    db_session.commit()
    
    # Test initial creation
    doc1 = get_or_create_document(db_session, run.id, temp_document)
    assert doc1 is not None
    assert doc1.name == os.path.basename(temp_document)
    
    # Test deduplication (same file returns same document without creating new one)
    doc2 = get_or_create_document(db_session, run.id, temp_document)
    assert doc1.id == doc2.id
    
    # Test missing file error
    with pytest.raises(FileNotFoundError):
        get_or_create_document(db_session, run.id, temp_document + "_fake")


def test_chunk_service(db_session, temp_document):
    run = Run(status="running")
    db_session.add(run)
    db_session.commit()
    
    doc = get_or_create_document(db_session, run.id, temp_document)
    
    # Test bulk create
    contents = ["chunk 1", "chunk 2", "chunk 3"]
    chunks = create_chunks(db_session, doc.id, run.id, contents)
    
    assert len(chunks) == 3
    assert chunks[0].chunk_index == 0
    assert chunks[2].chunk_index == 2
    assert chunks[1].text == "chunk 2"
    
    # Test fetch
    fetched = get_chunk(db_session, chunks[0].id)
    assert fetched is not None
    assert fetched.id == chunks[0].id
    assert get_chunk(db_session, uuid.uuid4()) is None


def test_extraction_and_verification_services(db_session, temp_document):
    run = Run(status="running")
    db_session.add(run)
    db_session.commit()
    
    doc = get_or_create_document(db_session, run.id, temp_document)
    chunks = create_chunks(db_session, doc.id, run.id, ["test chunk"])
    chunk_id = chunks[0].id
    
    # Test finding creation
    finding = create_finding(
        db_session, 
        run.id, 
        title="Sky is blue",
        status="pending",
        severity="low",
        payload={"raw_text": "The sky is blue", "confidence": 0.95}
    )
    assert finding.id is not None
    assert finding.title == "Sky is blue"
    
    # Test claim creation
    claim = create_claim(
        db_session,
        run.id,
        finding.id,
        statement="Sky == Blue",
        confidence=0.99
    )
    assert claim.id is not None
    
    # Test evidence creation
    evidence = add_evidence(
        db_session,
        claim.id,
        chunk_id,
        relevance=1.0,
        snippet="Found in chunk"
    )
    assert evidence.id is not None
    assert evidence.relevance == 1.0


def test_audit_service(db_session):
    run = Run(status="running")
    db_session.add(run)
    db_session.commit()
    
    # Test audit log
    log = create_audit_log(db_session, run.id, action="test_action", details={"foo": "bar"})
    assert log.id is not None
    assert log.action == "test_action"
    
    # Test cost report
    cost = record_cost(
        db_session,
        run.id,
        total_cost_micro=10000,
        currency="USD",
        breakdown={"step": "extract", "input_tokens": 100, "output_tokens": 50}
    )
    assert cost.id is not None
    assert cost.total_cost_micro == 10000
