"""Structural LangGraph graph for FlowDocs 

This module defines the *shape* of the workflow graph and nothing else. Each
node is a typed placeholder that returns a partial ``WorkflowState`` update
advancing ``current_stage`` and ``completed_stages``. None of the nodes
perform real work at Step 4 — they exist so that the graph compiles, the
node/edge set is committed, and downstream steps can fill in real behaviour
without having to renegotiate the topology.

Topology::

    START
      -> ingest
      -> extract
      -> analyze
      -> verify
      -> approval
      -> complete
      -> END

Notes:

* The graph uses :data:`WorkflowState` as the state schema, matching the
  contract defined in :mod:`app.workflow.state`.
* Edges are plain sequential edges — no conditional routing yet. The real
  approval stage will eventually introduce a conditional edge
  (``approval -> complete`` or ``approval -> finalize``); that is explicitly
  deferred to a later step.
* The graph is compiled at import time and exposed as :data:`workflow_graph`.
  Calling code can ``await workflow_graph.ainvoke(state)`` without having to
  rebuild the topology on every invocation.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

import hashlib
import os
import uuid
from sqlalchemy.exc import IntegrityError
from app.db.session import get_session_factory
from app.models import Document, Run, DocumentChunk, Claim, ClaimEvidence, Finding, AuditLog
from app.llm.adapter import LLMAdapter
from app.llm.schemas import LLMRequest
from app.workflow.prompts import (
    EXTRACT_SYSTEM_PROMPT, ANALYZE_SYSTEM_PROMPT, VERIFY_SYSTEM_PROMPT,
    ExtractionResult, AnalysisResult, VerificationResult
)

from app.workflow.state import WorkflowState

# ---------------------------------------------------------------------------
# Node identifiers. Exposed as constants so tests and downstream code can
# refer to nodes by name without restating strings.
# ---------------------------------------------------------------------------

NODE_INGEST: str = "ingest"
NODE_EXTRACT: str = "extract"
NODE_ANALYZE: str = "analyze"
NODE_VERIFY: str = "verify"
NODE_APPROVAL: str = "approval"
NODE_COMPLETE: str = "complete"

EXPECTED_NODES: tuple[str, ...] = (
    NODE_INGEST,
    NODE_EXTRACT,
    NODE_ANALYZE,
    NODE_VERIFY,
    NODE_APPROVAL,
    NODE_COMPLETE,
)

# ---------------------------------------------------------------------------
# Structural node placeholders.
#
# Each node returns a partial state update. They intentionally do **no** work
# at this stage; they exist only to give the graph a topology. Real
# behaviour — DB reads, LLM calls, document parsing — is added in later
# steps. Every node returns the same partial-dict shape so that future real
# implementations can replace them one-for-one without changing the edges.
# ---------------------------------------------------------------------------


def ingest_node(state: WorkflowState) -> dict:
    """Real ingestion stage that reads a file and records it to the database.

    Returns a partial state update that records the transition from
    ``ingest`` to ``extract``. If the input is invalid, transitions to a controlled
    error state.
    """
    print("[DEBUG] ingest_node started!")
    run_id_str = state.get("run_id")
    if not run_id_str:
        return {
            "current_stage": "failed",
            "status": "failed",
            "errors": ["Missing run_id in state"],
        }
    
    try:
        run_uuid = uuid.UUID(run_id_str)
    except ValueError:
        return {
            "current_stage": "failed",
            "status": "failed",
            "errors": [f"Invalid run_id format: {run_id_str}"],
        }

    session_factory = get_session_factory()
    with session_factory() as session:
        run = session.get(Run, run_uuid)
        if not run:
            return {
                "current_stage": "failed",
                "status": "failed",
                "errors": [f"Run not found: {run_id_str}"],
            }
        
        input_metadata = run.input_metadata or {}
        file_paths = input_metadata.get("file_paths", [])
        if not file_paths:
            return {
                "current_stage": "failed",
                "status": "failed",
                "errors": ["Missing file_paths in Run.input_metadata"],
            }
        
        all_doc_ids = []
        all_chunk_ids = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                continue
                
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
            except OSError as e:
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": [f"Error reading file {file_path}: {e}"],
                }
            
            file_hash = hashlib.sha256(content).hexdigest()
            byte_size = len(content)
            name = os.path.basename(file_path)
            
            # Check for duplicate hash
            existing = session.query(Document).filter_by(hash=file_hash).first()
            if existing:
                all_doc_ids.append(str(existing.id))
                chunks = session.query(DocumentChunk).filter_by(document_id=existing.id).all()
                all_chunk_ids.extend([str(c.id) for c in chunks])
                continue
            
            # Parse content
            if name.lower().endswith(".pdf"):
                try:
                    import fitz
                    doc = fitz.open(stream=content, filetype="pdf")
                    text_content = ""
                    for page in doc:
                        text_content += page.get_text() + "\n\n"
                    doc.close()
                except Exception as e:
                    return {
                        "current_stage": "failed",
                        "status": "failed",
                        "errors": [f"Error parsing PDF {name}: {e}"],
                    }
            else:
                try:
                    text_content = content.decode("utf-8")
                except UnicodeDecodeError:
                    text_content = content.decode("latin-1")
                
            raw_chunks = [p.strip() for p in text_content.split("\n\n") if p.strip()]
            if not raw_chunks:
                raw_chunks = [text_content.strip()] if text_content.strip() else ["(Empty Document)"]
                
            document = Document(
                run_id=run.id,
                hash=file_hash,
                name=name,
                byte_size=byte_size,
                metadata_json={"source": file_path}
            )
            session.add(document)
            
            try:
                session.commit()
                all_doc_ids.append(str(document.id))
                
                db_chunks = []
                for i, text in enumerate(raw_chunks):
                    chunk = DocumentChunk(
                        document_id=document.id,
                        run_id=run.id,
                        chunk_index=i,
                        text=text
                    )
                    db_chunks.append(chunk)
                    session.add(chunk)
                session.commit()
                all_chunk_ids.extend([str(c.id) for c in db_chunks])
            except IntegrityError as e:
                session.rollback()
                existing = session.query(Document).filter_by(hash=file_hash).first()
                if existing:
                    all_doc_ids.append(str(existing.id))
                    chunks = session.query(DocumentChunk).filter_by(document_id=existing.id).all()
                    all_chunk_ids.extend([str(c.id) for c in chunks])
                else:
                    return {
                        "current_stage": "failed",
                        "status": "failed",
                        "errors": [f"Database error during ingestion: {e}"],
                    }
        
        if not all_doc_ids:
             return {
                "current_stage": "failed",
                "status": "failed",
                "errors": ["No valid documents ingested."],
            }
        
        return {
            "current_stage": NODE_EXTRACT,
            "completed_stages": [NODE_INGEST],
            "document_ids": all_doc_ids,
            "ingested_document_ids": all_doc_ids,
            "chunk_ids": all_chunk_ids,
            "chunk_count": len(all_chunk_ids),
        }


from app.config import get_settings

def get_llm():
    """Return the configured LLM adapter."""
    settings = get_settings()
    provider = settings.llm_provider.lower()
    
    if provider == "mock":
        from app.llm.mock import MockLLMAdapter
        return MockLLMAdapter()
    else:
        from app.llm.gemini import GeminiLLMAdapter
        return GeminiLLMAdapter()

def extract_node(state: WorkflowState) -> dict:
    """Extract claims from ingested document chunks using the LLM."""
    chunk_ids = state.get("chunk_ids", [])
    if not chunk_ids:
        return {
            "current_stage": NODE_ANALYZE,
            "completed_stages": state.get("completed_stages", []) + [NODE_EXTRACT],
        }

    session_factory = get_session_factory()
    llm = get_llm()
    
    previously_processed = set(state.get("processed_chunk_ids", []))
    extracted_claim_ids = list(state.get("extracted_claim_ids", []))
    processed_chunk_ids = list(state.get("processed_chunk_ids", []))
    
    with session_factory() as session:
        for chunk_id_str in chunk_ids:
            if chunk_id_str in previously_processed:
                continue
            
            chunk = session.get(DocumentChunk, uuid.UUID(chunk_id_str))
            if not chunk:
                continue
                
            # Check budget
            total_tokens_used = state.get("total_tokens_used", 0)
            token_budget = get_settings().llm_token_budget
            if total_tokens_used >= token_budget:
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": [f"Token budget exceeded ({total_tokens_used} >= {token_budget}). Requires continuation/retry."],
                }

            req = LLMRequest(
                system_prompt=EXTRACT_SYSTEM_PROMPT,
                user_prompt=f"Text to analyze:\n\n{chunk.text}",
                response_schema=ExtractionResult,
                max_output_tokens=1000,
                request_id=str(uuid.uuid4()),
                run_id=state.get("run_id"),
                node="extract",
                purpose="extract_claims_from_chunk"
            )
            
            try:
                resp = llm.generate(req)
                
                # Update tokens
                state["total_tokens_used"] = state.get("total_tokens_used", 0) + (resp.input_tokens + resp.output_tokens)
                
                parsed = resp.parsed_content
                if not parsed or not hasattr(parsed, "claims"):
                    continue
                    
                for extracted_claim in parsed.claims:
                    claim = Claim(
                        run_id=uuid.UUID(state.get("run_id")),
                        statement=extracted_claim.statement,
                        confidence=1.0,  # Or from LLM if we added it
                    )
                    session.add(claim)
                    session.flush() # get ID
                    
                    evidence = ClaimEvidence(
                        claim_id=claim.id,
                        chunk_id=chunk.id,
                        snippet=extracted_claim.exact_quote,
                    )
                    session.add(evidence)
                    extracted_claim_ids.append(str(claim.id))
                    
                processed_chunk_ids.append(str(chunk.id))
            except Exception as e:
                import traceback
                print(f"[ERROR] extract_node failed for chunk {chunk.id}: {e}")
                traceback.print_exc()                
                session.rollback()
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": state.get("errors", []) + [f"LLM extraction failed on chunk {chunk.id}: {str(e)}"]
                }
        session.commit()

    return {
        "current_stage": NODE_ANALYZE,
        "completed_stages": state.get("completed_stages", []) + [NODE_EXTRACT],
        "extracted_claim_ids": extracted_claim_ids,
        "extracted_entity_count": len(extracted_claim_ids),
        "processed_chunk_ids": processed_chunk_ids,
    }


def analyze_node(state: WorkflowState) -> dict:
    """Analyze extracted claims to identify findings and conflicts."""
    extracted_claim_ids = state.get("extracted_claim_ids", [])
    if not extracted_claim_ids:
        return {
            "current_stage": NODE_VERIFY,
            "completed_stages": state.get("completed_stages", []) + [NODE_ANALYZE],
            "analyzed_finding_ids": [],
            "analyzed_claim_ids": [],
        }

    session_factory = get_session_factory()
    llm = get_llm()
    
    previously_analyzed = set(state.get("analyzed_claim_ids", []))
    analyzed_finding_ids = list(state.get("analyzed_finding_ids", []))
    analyzed_claim_ids = list(state.get("analyzed_claim_ids", []))
    
    with session_factory() as session:
        claims = []
        old_claims = []
        for cid in extracted_claim_ids:
            claim = session.get(Claim, uuid.UUID(cid))
            if claim:
                if cid in previously_analyzed:
                    old_claims.append(claim)
                else:
                    claims.append(claim)
                    analyzed_claim_ids.append(str(claim.id))
                
        if claims:
            # Get compliance rules from the run
            run_id = uuid.UUID(state.get("run_id"))
            run = session.get(Run, run_id)
            compliance_rules = run.input_metadata.get("compliance_rules") if run and run.input_metadata else None
            
            # Fetch raw chunks for corpus
            chunk_objs = []
            corpus_parts = []
            for chunk_id_str in state.get("processed_chunk_ids", []):
                chunk = session.get(DocumentChunk, uuid.UUID(chunk_id_str))
                if chunk:
                    chunk_objs.append(chunk)
                    corpus_parts.append(f"--- Document Chunk {chunk.id} ---\n{chunk.text}")
                    
            # Collect old claims for context
            old_claims_text = ""
            if old_claims:
                old_claims_data = [f"Claim ID: {c.id}\nStatement: {c.statement}" for c in old_claims]
                old_claims_text = "Existing Baseline Claims (For Context Only):\n" + "\n".join(old_claims_data) + "\n\n"
                
            # Collect claims and their evidence snippets
            claims_data = []
            for c in claims:
                evidence_records = session.query(ClaimEvidence).filter(ClaimEvidence.claim_id == c.id).all()
                evidence_texts = [f" - {ev.snippet}" for ev in evidence_records if ev.snippet]
                evidence_block = "\n".join(evidence_texts) if evidence_texts else " - No evidence found"
                claims_data.append(f"Claim ID: {c.id}\nStatement: {c.statement}\nEvidence:\n{evidence_block}")
            
            claims_text = "New Extracted Claims and Evidence (To Evaluate):\n" + "\n\n".join(claims_data)
            
            user_prompt = old_claims_text + claims_text
            if compliance_rules:
                user_prompt += f"\n\nIMPORTANT COMPLIANCE RULES TO CHECK AGAINST:\n{compliance_rules}\n"
                user_prompt += "\nPlease evaluate every compliance rule against the New Extracted Claims. You MUST consider the Existing Baseline Claims to detect if a new claim contradicts an existing one. Create a finding for any discrepancy, violation, contradiction, or notable alignment caused by the New claims."
            
            # Check budget
            total_tokens_used = state.get("total_tokens_used", 0)
            token_budget = get_settings().llm_token_budget
            if total_tokens_used >= token_budget:
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": [f"Token budget exceeded ({total_tokens_used} >= {token_budget}). Requires continuation/retry."],
                }

            req = LLMRequest(
                system_prompt=ANALYZE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=AnalysisResult,
                max_output_tokens=1500,
                request_id=str(uuid.uuid4()),
                run_id=state.get("run_id"),
                node="analyze",
                purpose="compliance_and_conflict_analysis"
            )
            
            try:
                resp = llm.generate(req)
                
                # Update tokens
                state["total_tokens_used"] = state.get("total_tokens_used", 0) + (resp.input_tokens + resp.output_tokens)
                
                parsed = resp.parsed_content
                if parsed and hasattr(parsed, "findings"):
                    run_id = uuid.UUID(state.get("run_id"))
                    compliance_checks_total = state.get("compliance_checks_total", 0)
                    compliance_checks_passed = state.get("compliance_checks_passed", 0)
                    
                    for f_info in parsed.findings:
                        compliance_checks_total += 1
                        if getattr(f_info, "severity", None) == "passed":
                            compliance_checks_passed += 1
                            # We still want to create a finding so the human can review the passed check!
                            # We just increment the counter.

                        # Only create finding if it references valid extracted claims OR has new_claims (e.g. for missing requirements)
                        valid_cids = [cid for cid in getattr(f_info, "claim_ids", []) if cid in extracted_claim_ids]
                        new_claims_data = getattr(f_info, "new_claims", [])
                        
                        if not valid_cids and not new_claims_data:
                            continue
                            
                        finding = Finding(
                            run_id=run_id,
                            title=f_info.title,
                            summary=f_info.summary,
                            severity=f_info.severity,
                            status="pending"
                        )
                        session.add(finding)
                        session.flush()
                        
                        # Link existing claims to finding
                        for cid in valid_cids:
                            claim = session.get(Claim, uuid.UUID(cid))
                            if claim:
                                finding.claims.append(claim)
                                
                        # Process new claims (e.g. evidence of absence)
                        seen_claims = set()
                        for nc_data in new_claims_data:
                            # Determine best chunk to attach evidence to
                            matched_chunk = None
                            if nc_data.exact_quote:
                                for chunk in chunk_objs:
                                    if nc_data.exact_quote in chunk.text:
                                        matched_chunk = chunk
                                        break
                            if not matched_chunk and chunk_objs:
                                matched_chunk = chunk_objs[0] # Fallback
                                
                            chunk_id_str = str(matched_chunk.id) if matched_chunk else "none"
                            claim_sig = (nc_data.statement.strip().lower(), chunk_id_str)
                            if claim_sig in seen_claims:
                                continue
                            seen_claims.add(claim_sig)

                            new_claim = Claim(
                                run_id=run_id,
                                statement=nc_data.statement,
                                confidence=1.0,
                            )
                            session.add(new_claim)
                            session.flush()
                            finding.claims.append(new_claim)
                            
                            if matched_chunk:
                                evidence = ClaimEvidence(
                                    claim_id=new_claim.id,
                                    chunk_id=matched_chunk.id,
                                    snippet=nc_data.exact_quote,
                                    relevance=1.0
                                )
                                session.add(evidence)
                                
                        analyzed_finding_ids.append(str(finding.id))
                        
                    # Update state with the counts
                    state["compliance_checks_total"] = compliance_checks_total
                    state["compliance_checks_passed"] = compliance_checks_passed
                        
                session.commit()
            except Exception as e:
                import traceback
                print(f"[ERROR] analyze_node failed: {e}")
                traceback.print_exc()
                session.rollback()
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": state.get("errors", []) + [f"LLM analysis failed: {str(e)}"]
                }

    return {
        "current_stage": NODE_VERIFY,
        "completed_stages": state.get("completed_stages", []) + [NODE_ANALYZE],
        "analyzed_finding_ids": analyzed_finding_ids,
        "analyzed_claim_ids": analyzed_claim_ids,
    }


def verify_node(state: WorkflowState) -> dict:
    """Verify claims against their source evidence."""
    # ALWAYS check if human review is required first, so early returns don't skip it
    run_id_str = state.get("run_id")
    approval_required = False
    
    if run_id_str:
        try:
            run_id = uuid.UUID(run_id_str) if isinstance(run_id_str, str) else run_id_str
            session_factory = get_session_factory()
            with session_factory() as session:
                pending_count = session.query(Finding).filter(
                    Finding.run_id == run_id, 
                    Finding.status == "pending"
                ).count()
                approval_required = pending_count > 0
        except ValueError:
            pass # Handle invalid UUIDs in tests

    extracted_claim_ids = state.get("extracted_claim_ids", [])
    if not extracted_claim_ids:
        return {
            "current_stage": NODE_APPROVAL if approval_required else NODE_COMPLETE,
            "completed_stages": state.get("completed_stages", []) + [NODE_VERIFY],
            "verified_claim_ids": [],
            "verification_result_counts": {},
            "failed_insufficient_evidence_count": 0,
            "approval_required": approval_required,
        }

    session_factory = get_session_factory()
    llm = get_llm()
    
    previously_verified = set(state.get("verified_claim_ids", []))
    verified_claim_ids = list(state.get("verified_claim_ids", []))
    
    # Initialize counts from previous state to accumulate instead of replace
    prev_counts = state.get("verification_result_counts", {})
    result_counts = {
        "verified": prev_counts.get("verified", 0),
        "contradicted": prev_counts.get("contradicted", 0),
        "insufficient_evidence": prev_counts.get("insufficient_evidence", 0)
    }
    
    with session_factory() as session:
        for cid in extracted_claim_ids:
            if cid in previously_verified:
                continue
            
            claim = session.get(Claim, uuid.UUID(cid))
            if not claim:
                continue
                
            evidence_records = session.query(ClaimEvidence).filter(ClaimEvidence.claim_id == claim.id).all()
            if not evidence_records:
                continue
                
            # For simplicity, verify against the first piece of evidence
            # In a real setup, we might verify against all chunk texts
            evidence = evidence_records[0]
            chunk = session.get(DocumentChunk, evidence.chunk_id)
            if not chunk:
                continue
                
            # Check budget
            total_tokens_used = state.get("total_tokens_used", 0)
            token_budget = get_settings().llm_token_budget
            if total_tokens_used >= token_budget:
                return {
                    "current_stage": "failed",
                    "status": "failed",
                    "errors": [f"Token budget exceeded ({total_tokens_used} >= {token_budget}). Requires continuation/retry."],
                }

            req = LLMRequest(
                system_prompt=VERIFY_SYSTEM_PROMPT,
                user_prompt=f"Claim:\n{claim.statement}\n\nEvidence source:\n{evidence.snippet or chunk.text}",
                response_schema=VerificationResult,
                max_output_tokens=200,
                request_id=str(uuid.uuid4()),
                run_id=state.get("run_id"),
                node="verify",
                purpose="claim_verification"
            )
            
            try:
                resp = llm.generate(req)
                
                # Update tokens
                state["total_tokens_used"] = state.get("total_tokens_used", 0) + (resp.input_tokens + resp.output_tokens)
                
                parsed = resp.parsed_content
                if parsed:
                    # Update evidence relevance
                    evidence.relevance = parsed.relevance_score
                    
                    # Track result
                    res_type = parsed.supports_claim
                    if res_type in result_counts:
                        result_counts[res_type] += 1
                        
                    if res_type == "verified":
                        verified_claim_ids.append(str(claim.id))
                        
            except Exception as e:
                import traceback
                print(f"[ERROR] verify_node failed for claim {claim.id}: {e}")
                traceback.print_exc()
                
        session.commit()

    return {
        "current_stage": NODE_APPROVAL if approval_required else NODE_COMPLETE,
        "completed_stages": state.get("completed_stages", []) + [NODE_VERIFY],
        "verified_claim_ids": verified_claim_ids,
        "verification_result_counts": result_counts,
        "failed_insufficient_evidence_count": result_counts.get("insufficient_evidence", 0),
        "approval_required": approval_required,
    }


def approval_node(state: WorkflowState) -> dict:
    """Structural placeholder for the approval gate.

    Real approval logic (reviewer assignment, decision routing) is added in a
    later step. This placeholder simply advances the stage and records the
    transition. No human-in-the-loop behaviour is implemented here.
    """
    return {
        "current_stage": NODE_COMPLETE,
        "completed_stages": [
            NODE_INGEST,
            NODE_EXTRACT,
            NODE_ANALYZE,
            NODE_VERIFY,
            NODE_APPROVAL,
        ],
    }


def complete_node(state: WorkflowState) -> dict:
    """Mark the workflow as completed."""
    run_id_str = state.get("run_id")
    if not run_id_str:
        return {
            "status": "completed",
            "current_stage": NODE_COMPLETE
        }
        
    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            run_id = uuid.UUID(run_id_str) if isinstance(run_id_str, str) else run_id_str
            run = session.get(Run, run_id)
            if run:
                run.status = "completed"
                session.add(AuditLog(
                    run_id=run.id,
                    actor="system",
                    action="workflow_completed",
                    payload={"stage": NODE_COMPLETE}
                ))
                session.commit()
                
                meta = dict(run.input_metadata or {})
        except ValueError:
            pass
            report_meta = meta.get("report_metadata", {})
            
            prev_version = report_meta.get("new_version", 0)
            new_version = prev_version + 1
            
            all_findings = session.query(Finding).filter(Finding.run_id == run.id).all()
            current_finding_titles = [f.title for f in all_findings]
            
            prev_titles = report_meta.get("all_titles", [])
            
            changed = [t for t in current_finding_titles if t not in prev_titles]
            unchanged = [t for t in prev_titles if t in current_finding_titles]
            
            new_report_meta = {
                "previous_version": prev_version,
                "new_version": new_version,
                "changed_sections": changed,
                "unchanged_sections": unchanged,
                "all_titles": current_finding_titles,
                "source_document_ids": state.get("ingested_document_ids", []),
                "triggered_by": "incremental_update" if prev_version > 0 else "initial_run"
            }
            
            meta["report_metadata"] = new_report_meta
            run.input_metadata = meta
            session.commit()
            
    return {
        "current_stage": "completed",
        "status": "completed",
        "completed_stages": state.get("completed_stages", []) + [NODE_COMPLETE],
    }



def requires_human_review(state: WorkflowState) -> str:
    """Determine whether to route to human review or skip straight to completion."""
    if state.get("approval_required", False):
        return NODE_APPROVAL
    return NODE_COMPLETE


def _build_graph() -> StateGraph:
    """Construct the LangGraph ``StateGraph`` and return it uncompiled."""
    graph = StateGraph(WorkflowState)

    graph.add_node(NODE_INGEST, ingest_node)
    graph.add_node(NODE_EXTRACT, extract_node)
    graph.add_node(NODE_ANALYZE, analyze_node)
    graph.add_node(NODE_VERIFY, verify_node)
    graph.add_node(NODE_APPROVAL, approval_node)
    graph.add_node(NODE_COMPLETE, complete_node)

    graph.add_edge(START, NODE_INGEST)
    graph.add_edge(NODE_INGEST, NODE_EXTRACT)
    graph.add_edge(NODE_EXTRACT, NODE_ANALYZE)
    graph.add_edge(NODE_ANALYZE, NODE_VERIFY)
    
    graph.add_conditional_edges(
        NODE_VERIFY,
        requires_human_review,
        {
            NODE_APPROVAL: NODE_APPROVAL,
            NODE_COMPLETE: NODE_COMPLETE,
        }
    )
    
    graph.add_edge(NODE_APPROVAL, NODE_COMPLETE)
    graph.add_edge(NODE_COMPLETE, END)

    return graph


def compile_workflow(checkpointer=None, **kwargs):
    """Compile the graph, optionally with a checkpointer and kwargs like interrupt_before."""
    return _build_graph().compile(checkpointer=checkpointer, **kwargs)

#: The compiled, ready-to-invoke workflow graph without a checkpointer.
#: Calling code can use this directly or call compile_workflow(checkpointer).
workflow_graph = compile_workflow()


__all__ = [
    "EXPECTED_NODES",
    "NODE_INGEST",
    "NODE_EXTRACT",
    "NODE_ANALYZE",
    "NODE_VERIFY",
    "NODE_APPROVAL",
    "NODE_COMPLETE",
    "workflow_graph",
    "compile_workflow",
]
