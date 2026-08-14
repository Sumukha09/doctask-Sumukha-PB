import uuid
import pytest
from app.workflow.graph import extract_node, analyze_node, verify_node, NODE_ANALYZE, NODE_VERIFY, NODE_APPROVAL
from app.workflow.state import WorkflowState
from app.models import Document, DocumentChunk, Claim, ClaimEvidence, Finding, Run
from app.llm.mock import MockLLMAdapter
from app.workflow.prompts import ExtractionResult, ExtractedClaim, AnalysisResult, ExtractedFinding, VerificationResult
from pydantic import BaseModel

@pytest.fixture
def mock_llm(monkeypatch):
    adapter = MockLLMAdapter()
    monkeypatch.setattr("app.workflow.graph.get_llm", lambda: adapter)
    return adapter

def test_extract_node_real(db_session, mock_llm):
    # Setup Document and Chunk
    run = Run(id=uuid.uuid4(), input_metadata={"file_path": "test.txt"})
    db_session.add(run)
    doc = Document(run_id=run.id, hash="hash1", name="test.txt", byte_size=10, metadata_json={})
    db_session.add(doc)
    db_session.commit()
    
    chunk = DocumentChunk(document_id=doc.id, run_id=run.id, chunk_index=0, text="Mock text with claim.")
    db_session.add(chunk)
    db_session.commit()

    # Configure MockLLMAdapter
    extracted_res = ExtractionResult(claims=[ExtractedClaim(statement="Test claim", exact_quote="Mock text")])
    mock_llm.queue_response(parsed_content=extracted_res)

    state = WorkflowState(chunk_ids=[str(chunk.id)], completed_stages=["ingest"])
    new_state = extract_node(state)

    assert new_state["current_stage"] == NODE_ANALYZE
    assert "extract" in new_state["completed_stages"]
    assert new_state["extracted_entity_count"] == 1
    
    claim_id = new_state["extracted_claim_ids"][0]
    claim = db_session.get(Claim, uuid.UUID(claim_id))
    assert claim is not None
    assert claim.statement == "Test claim"
    
    evidence = db_session.query(ClaimEvidence).filter_by(claim_id=claim.id).first()
    assert evidence is not None
    assert evidence.snippet == "Mock text"


def test_analyze_node_real(db_session, mock_llm):
    run = Run(id=uuid.uuid4(), input_metadata={"file_path": "test.txt"})
    db_session.add(run)
    db_session.commit()
    
    claim1 = Claim(run_id=run.id, statement="It is 2024", confidence=1.0)
    claim2 = Claim(run_id=run.id, statement="It is 2025", confidence=1.0)
    db_session.add_all([claim1, claim2])
    db_session.commit()
    
    analysis_res = AnalysisResult(findings=[
        ExtractedFinding(title="Date mismatch", summary="Conflict", severity="high", claim_ids=[str(claim1.id), str(claim2.id)])
    ])
    mock_llm.queue_response(parsed_content=analysis_res)

    state = WorkflowState(extracted_claim_ids=[str(claim1.id), str(claim2.id)], completed_stages=["extract"])
    new_state = analyze_node(state)

    assert new_state["current_stage"] == NODE_VERIFY
    finding_id = new_state["analyzed_finding_ids"][0]
    finding = db_session.get(Finding, uuid.UUID(finding_id))
    
    assert finding is not None
    assert finding.title == "Date mismatch"
    assert len(finding.claims) == 2


def test_verify_node_real(db_session, mock_llm):
    run = Run(id=uuid.uuid4(), input_metadata={"file_path": "test.txt"})
    db_session.add(run)
    doc = Document(run_id=run.id, hash="hash2", name="t.txt", byte_size=10, metadata_json={})
    db_session.add(doc)
    db_session.commit()
    
    chunk = DocumentChunk(document_id=doc.id, run_id=run.id, chunk_index=0, text="The sky is blue")
    db_session.add(chunk)
    claim = Claim(run_id=run.id, statement="The sky is blue", confidence=1.0)
    db_session.add(claim)
    db_session.commit()
    
    evidence = ClaimEvidence(claim_id=claim.id, chunk_id=chunk.id, snippet="sky is blue")
    db_session.add(evidence)
    db_session.commit()

    verif_res = VerificationResult(supports_claim="verified", relevance_score=0.9, explanation="Exact match")
    mock_llm.queue_response(parsed_content=verif_res)

    state = WorkflowState(extracted_claim_ids=[str(claim.id)], completed_stages=["analyze"])
    new_state = verify_node(state)

    assert new_state["current_stage"] == NODE_APPROVAL
    assert new_state["verified_claim_ids"] == [str(claim.id)]
    assert new_state["verification_result_counts"]["verified"] == 1
