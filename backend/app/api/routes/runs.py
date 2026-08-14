"""API routes for managing workflow runs."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from langgraph.checkpoint.postgres import PostgresSaver

from app.api.deps import get_checkpointer, get_db_session
from app.api.schemas.run import RunCreateRequest, RunResponse, RunStateResponse, RunDetailsResponse, RunStatsResponse, AuditLogResponse, CostReportResponse
from app.api.schemas.approval import ApprovalRequest
from app.models.run import Run
from app.models.document import Document
from app.models.finding import Finding
from app.models.claim import Claim
from app.models.cost_report import CostReport
from app.models.audit_log import AuditLog
from app.models.claim_evidence import ClaimEvidence as Evidence
from app.services.run import get_run
from app.services.audit import create_audit_log
from app.workflow.graph import compile_workflow

router = APIRouter(prefix="/runs", tags=["runs"])

@router.get("/run_pytest")
def run_pytest_route():
    import subprocess
    try:
        # Run pytest and capture output
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/"],
            capture_output=True,
            text=True,
            cwd="/app"
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "trace": traceback.format_exc()}



from fastapi import BackgroundTasks
import logging

def run_graph_background(run_id_str: str, initial_state: dict):
    from app.config import get_settings
    settings = get_settings()
    conn_string = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    try:
        with PostgresSaver.from_conn_string(conn_string) as saver:
            saver.setup()
            graph = compile_workflow(checkpointer=saver, interrupt_before=["approval"])
            thread_config = {"configurable": {"thread_id": run_id_str}}
            final_state = graph.invoke(initial_state, thread_config)
            
            # Extract final stage to update DB status
            current_stage = final_state.get("current_stage")

            from app.db.session import get_session_factory
            from app.models.run import Run
            import uuid
            
            session_factory = get_session_factory()
            with session_factory() as session:
                run = session.get(Run, uuid.UUID(run_id_str))
                if run:
                    if final_state.get("status") == "failed":
                        run.status = "failed"
                    elif current_stage == "completed":
                        run.status = "completed"
                    elif current_stage == "failed":
                        run.status = "failed"
                    elif current_stage == "approval":
                        # If genuinely waiting for approval, keep it waiting.
                        pass # leaving it running/pending_approval depending on what it currently is
                    
                    session.commit()
    except Exception as e:
        import traceback
        print(f"[ERROR] Graph execution failed for run {run_id_str}: {e}")
        traceback.print_exc()
        try:
            from app.db.session import get_session_factory
            from app.models.run import Run
            import uuid
            session_factory = get_session_factory()
            with session_factory() as session:
                run = session.get(Run, uuid.UUID(run_id_str))
                if run:
                    run.status = "failed"
                    if run.input_metadata is None:
                        run.input_metadata = {}
                    meta = dict(run.input_metadata)
                    meta["error"] = str(e)
                    run.input_metadata = meta
                    session.commit()
        except:
            pass

@router.post(
    "",
    response_model=RunStateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new document processing run",
)
def create_run(
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
) -> RunStateResponse:
    """Create a new run and invoke the workflow graph."""
    print(f"[DEBUG] create_run endpoint hit! request files count: {len(request.files)}")

    file_paths = []
    
    for f in request.files:
        path = f.file_path
        if f.file_content_base64:
            import base64
            import tempfile
            import os
            
            content = base64.b64decode(f.file_content_base64)
            name = f.file_name or "uploaded_doc.pdf"
            upload_dir = os.path.join(os.getcwd(), "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, name)
            with open(path, "wb") as file_out:
                file_out.write(content)
        
        if path:
            file_paths.append(path)

    if not file_paths:
        raise HTTPException(status_code=400, detail="Must provide at least one valid file_path or file_content_base64")

    # 1. Create the database record
    run = Run(status="running", input_metadata={
        "file_paths": file_paths,
        "compliance_rules": request.compliance_rules
    })
    db.add(run)
    db.commit()
    
    run_id_str = str(run.id)
    print(f"[DEBUG] DB commit successful. run_id: {run_id_str}")
    
    # 2. Setup initial state
    initial_state = {
        "run_id": run_id_str,
        "current_stage": "ingest",
    }
    
    # 3. Schedule graph in background
    print(f"[DEBUG] Scheduling run_graph_background task for run {run_id_str}...")
    background_tasks.add_task(run_graph_background, run_id_str, initial_state)
        
    print(f"[DEBUG] Returning initial state for run {run_id_str}")
    return RunStateResponse(**initial_state)


@router.post(
    "/{run_id}/documents",
    status_code=status.HTTP_201_CREATED,
    summary="Add documents to an existing run",
)
def add_documents_to_run(
    run_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
):
    """Upload new documents to an existing run and selectively process them."""
    import os
    import hashlib
    
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found."
        )
        
    # Read files and hash them
    new_paths = []
    response_docs = []
    upload_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    for f in files:
        if not f.filename:
            continue
            
        content = f.file.read()
        if not content:
            raise HTTPException(status_code=400, detail=f"File {f.filename} is empty")
            
        # Check size limit (e.g. 50MB)
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File {f.filename} exceeds 50MB limit")
            
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Check if already added to this run
        existing_doc = db.query(Document).filter_by(hash=file_hash, run_id=run.id).first()
        if existing_doc:
            response_docs.append({
                "document_id": str(existing_doc.id),
                "filename": f.filename,
                "status": "already_exists"
            })
            continue
            
        # Save file to disk
        path = os.path.join(upload_dir, f.filename)
        with open(path, "wb") as out_file:
            out_file.write(content)
            
        new_paths.append(path)
        response_docs.append({
            "filename": f.filename,
            "status": "queued"
        })
        
    if not new_paths:
        # All were duplicates, return idempotent success
        return {
            "run_id": str(run_id),
            "added_documents": response_docs,
            "existing_documents": [str(d.id) for d in run.documents],
            "run_status": run.status
        }
        
    # Append to run.input_metadata
    meta = dict(run.input_metadata or {})
    current_paths = meta.get("file_paths", [])
    meta["file_paths"] = current_paths + new_paths
    run.input_metadata = meta
    
    # Update run status
    run.status = "running"
    db.commit()
    
    # Resume graph processing from ingest
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    
    # Update LangGraph state to trick it into restarting from start node
    # This prevents the graph from instantly terminating if it was previously at END.
    try:
        from langgraph.graph import START
        graph.update_state(thread_config, {"current_stage": "ingest", "status": "running"}, as_node=START)
    except Exception as e:
        print(f"[ERROR] Failed to update state pointer to START: {e}")
        # fallback, may not work if graph is completed
        graph.update_state(thread_config, {"current_stage": "ingest", "status": "running"})
        
    # Start background task with empty initial_state, it will pick up from the updated checkpoint
    background_tasks.add_task(run_graph_background, str(run_id), {})
    
    return {
        "run_id": str(run_id),
        "added_documents": response_docs,
        "existing_documents": [str(d.id) for d in run.documents],
        "run_status": "running"
    }


@router.get(
    "",
    response_model=list[RunResponse],
    summary="List all runs",
)
def list_runs(
    db: Session = Depends(get_db_session),
) -> list[RunResponse]:
    """Retrieve all runs ordered by created_at descending."""
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    return [RunResponse.model_validate(r) for r in runs]


@router.post(
    "/{run_id}/commit_clean",
    summary="Commit a run with zero pending findings",
)
def commit_clean_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
):
    """Manually advance the workflow when there are no findings to review."""
    pending_count = db.query(Finding).filter(Finding.run_id == run_id, Finding.status == "pending").count()
    if pending_count > 0:
        raise HTTPException(status_code=400, detail="Cannot commit cleanly while findings are pending.")

    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    
    # Update the state to indicate approval is complete
    graph.update_state(
        thread_config,
        {"approval_decision": "approved", "reviewer": "human_manual"},
        as_node="verify"
    )
    
    try:
        final_state = graph.invoke(None, thread_config)
        current_stage = final_state.get("current_stage")
        run = db.query(Run).filter(Run.id == run_id).first()
        if run:
            if current_stage == "completed":
                run.status = "completed"
            elif current_stage == "failed":
                run.status = "failed"
            db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow failed to resume."
        ) from e
        
    return {"status": "success"}

@router.post(
    "/{run_id}/resume",
    response_model=RunStateResponse,
    summary="Resume a stalled run",
)
def resume_run(
    run_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
) -> RunStateResponse:
    """Resume a stalled workflow run."""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found."
        )
        
    if run.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume a completed run."
        )
        
    run_id_str = str(run.id)
    
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": run_id_str}}
    state_snapshot = graph.get_state(thread_config)
    
    initial_state = {}
    if state_snapshot and state_snapshot.values:
        initial_state = state_snapshot.values
    else:
        initial_state = {
            "run_id": run_id_str,
            "current_stage": "ingest",
        }
        
    run.status = "running"
    db.commit()
    
    print(f"[DEBUG] Resuming run_graph_background task for run {run_id_str}...")
    background_tasks.add_task(run_graph_background, run_id_str, initial_state)
    
    return RunStateResponse(**initial_state)


@router.get(
    "/{run_id}",
    response_model=RunResponse,
    summary="Get run status",
)
def get_run_status(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> RunResponse:
    """Retrieve the basic database status of a run."""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found."
        )
        
    return RunResponse.model_validate(run)


@router.get(
    "/{run_id}/state",
    response_model=RunStateResponse,
    summary="Get run workflow state",
)
def get_run_state(
    run_id: uuid.UUID,
    checkpointer: PostgresSaver = Depends(get_checkpointer),
) -> RunStateResponse:
    """Retrieve the durable LangGraph state for a run."""
    
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    
    state_snapshot = graph.get_state(thread_config)
    
    state = {}
    if state_snapshot and state_snapshot.values:
        state = dict(state_snapshot.values)
    else:
        state = {"run_id": str(run_id), "current_stage": "ingest"}
        
    # Inject DB status and errors if the run failed outside the graph
    from app.db.session import get_session_factory
    from app.models.run import Run
    session_factory = get_session_factory()
    with session_factory() as session:
        run = session.get(Run, run_id)
        if run:
            if run.status == "failed":
                state["status"] = "failed"
                if run.input_metadata and "error" in run.input_metadata:
                    errors = state.get("errors") or []
                    errors.append(run.input_metadata["error"])
                    state["errors"] = errors
            elif not state.get("status"):
                state["status"] = run.status
                
    return RunStateResponse(**state)


@router.get(
    "/{run_id}/details",
    response_model=RunDetailsResponse,
    summary="Get detailed run information including documents and findings",
)
def get_run_details(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
) -> RunDetailsResponse:
    """Retrieve detailed UI-ready data for a run."""
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    state_snapshot = graph.get_state(thread_config)
    
    doc_ids = []
    if state_snapshot and state_snapshot.values:
        doc_ids = state_snapshot.values.get("document_ids", [])
        
    if doc_ids:
        docs = db.query(Document).filter(Document.id.in_([uuid.UUID(d) for d in doc_ids])).all()
    else:
        docs = []
        
    findings = db.query(Finding).filter(Finding.run_id == run_id).all()
    
    doc_details = [
        {"id": d.id, "name": d.name, "byte_size": d.byte_size}
        for d in docs
    ]
    
    finding_details = []
    for f in findings:
        claim_details = []
        for c in f.claims:
            evidence_details = []
            for e in c.evidence:
                evidence_details.append({
                    "id": e.id,
                    "snippet": e.snippet,
                    "relevance": e.relevance,
                    "document_name": e.chunk.document.name if e.chunk and e.chunk.document else None
                })
            claim_details.append({
                "id": c.id,
                "statement": c.statement,
                "confidence": c.confidence,
                "evidence": evidence_details
            })
        finding_details.append({
            "id": f.id,
            "title": f.title,
            "summary": f.summary,
            "severity": f.severity,
            "status": f.status,
            "claims": claim_details
        })
        
    return RunDetailsResponse(
        run_id=run_id,
        documents=doc_details,
        findings=finding_details
    )

@router.post(
    "/{run_id}/findings/{finding_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Submit a human review decision for a finding",
)
def approve_finding(
    run_id: uuid.UUID,
    finding_id: uuid.UUID,
    request: ApprovalRequest,
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
) -> dict:
    """Record a human reviewer's decision for a specific finding.
    
    If all findings for the run are reviewed, the workflow automatically resumes.
    """
    # 1. Fetch the finding securely scoped to the run
    finding = db.query(Finding).filter(
        Finding.id == finding_id, 
        Finding.run_id == run_id
    ).with_for_update().first()  # row-level lock for concurrency protection
    
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found for this run."
        )
        
    # 2. Concurrency/Stale Check: Ensure finding is still pending
    if finding.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Finding has already been reviewed (current status: {finding.status})."
        )
        
    # 3. Apply decision
    if request.decision == "approve":
        finding.status = "approved"
    elif request.decision == "reject":
        finding.status = "rejected"
    elif request.decision == "edit":
        finding.status = "approved"
    
    # 4. Handle edits properly without destroying auditability
    if request.decision == "edit" and request.edited_text:
        # We don't overwrite payload if it's somehow none, but it shouldn't be
        if finding.payload is None:
            finding.payload = {}
        
        # Preserve original summary
        payload_copy = dict(finding.payload)
        payload_copy["original_summary"] = finding.summary
        finding.payload = payload_copy
        
        # Apply the edit
        finding.summary = request.edited_text
        
    # 5. Record the action cleanly in the audit log
    create_audit_log(
        session=db,
        run_id=run_id,
        action=f"finding_{request.decision}",
        details={
            "finding_id": str(finding_id),
            "comment": request.comment,
            "edited_text": request.edited_text if request.decision == "edit" else None,
            "reviewer": "human"  # Placeholder until real auth exists
        }
    )
    
    db.commit()
    
    # 6. Check if we need to resume the workflow
    pending_count = db.query(Finding).filter(
        Finding.run_id == run_id, 
        Finding.status == "pending"
    ).count()
    
    if pending_count == 0:
        # All findings are reviewed! Update the graph state and resume.
        graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
        thread_config = {"configurable": {"thread_id": str(run_id)}}
        
        # Update the state to indicate approval is complete
        graph.update_state(
            thread_config,
            {"approval_decision": "approved", "reviewer": "human"},
            as_node="verify" # Provide the update as if it came from verify, to proceed safely
        )
        
        # Resume the workflow by invoking it with no new input
        try:
            final_state = graph.invoke(None, thread_config)
            
            current_stage = final_state.get("current_stage")
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                if current_stage == "completed":
                    run.status = "completed"
                elif current_stage == "failed":
                    run.status = "failed"
                db.commit()
                
        except Exception as e:
            # Again, log the error safely without exposing raw traces
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow failed to resume."
            ) from e
            
    return {"status": "success", "remaining_pending": pending_count}

@router.get(
    "/stats/global",
    response_model=RunStatsResponse,
    summary="Get global workflow statistics",
)
def get_global_stats(db: Session = Depends(get_db_session)) -> RunStatsResponse:
    """Retrieve aggregate statistics across all runs."""
    total_runs = db.query(Run).count()
    active_runs = db.query(Run).filter(Run.status.in_(["pending", "running"])).count()
    successful_runs = db.query(Run).filter(Run.status == "completed").count()
    failed_runs = db.query(Run).filter(Run.status == "failed").count()
    
    total_docs = db.query(Document).count()
    total_claims = db.query(Claim).count()
    total_findings = db.query(Finding).count()
    
    pending_approvals = db.query(Finding).filter(Finding.status == "pending").count()
    
    from sqlalchemy.sql import func
    total_cost_micro = db.query(func.sum(CostReport.total_cost_micro)).scalar() or 0
    
    return RunStatsResponse(
        total_runs=total_runs,
        active_runs=active_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        total_documents=total_docs,
        total_claims=total_claims,
        total_findings=total_findings,
        pending_approvals=pending_approvals,
        total_cost_micro=int(total_cost_micro)
    )

@router.get(
    "/{run_id}/audit",
    response_model=list[AuditLogResponse],
    summary="Get audit logs for a run",
)
def get_run_audit(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> list[AuditLogResponse]:
    """Retrieve chronological audit trail for a run."""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    logs = db.query(AuditLog).filter(AuditLog.run_id == run_id).order_by(AuditLog.created_at.asc()).all()
    return [AuditLogResponse.model_validate(log) for log in logs]

@router.get(
    "/{run_id}/cost",
    response_model=CostReportResponse,
    summary="Get cost report for a run",
)
def get_run_cost(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> CostReportResponse:
    """Retrieve LLM cost observability data for a run."""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    cost = db.query(CostReport).filter(CostReport.run_id == run_id).first()
    if not cost:
        raise HTTPException(status_code=404, detail="Cost report not found for run")
        
    return CostReportResponse.model_validate(cost)


from fastapi.responses import StreamingResponse
import io

@router.get(
    "/{run_id}/report",
    summary="Download the final verified PDF report",
)
def download_report(
    run_id: uuid.UUID,
    db: Session = Depends(get_db_session),
    checkpointer: PostgresSaver = Depends(get_checkpointer),
):
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    findings = db.query(Finding).filter(Finding.run_id == run_id, Finding.status == "approved").all()
    
    # Get stats from state
    from app.workflow.graph import compile_workflow
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
    thread_config = {"configurable": {"thread_id": str(run_id)}}
    state_snapshot = graph.get_state(thread_config)
    
    total_checks = 0
    passed_checks = 0
    if state_snapshot and state_snapshot.values:
        total_checks = state_snapshot.values.get("compliance_checks_total", 0)
        passed_checks = state_snapshot.values.get("compliance_checks_passed", 0)
    
    # Generate PDF in memory
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph(f"Verified Deliverable: Run {str(run_id)[:8]}", styles['Title']))
    story.append(Spacer(1, 12))
    

    story.append(Paragraph(f"<b>Findings:</b> {len(findings)}", styles['Normal']))
    if not findings:
        story.append(Paragraph("<b>Status:</b> NO FINDINGS", styles['Normal']))
    else:
        story.append(Paragraph("<b>Status:</b> FINDINGS PRESENT", styles['Normal']))
        
    story.append(Spacer(1, 12))
    
    if not findings:
        story.append(Paragraph("No verified findings to report. The corpus is clean.", styles['Normal']))
    else:
        for finding in findings:
            story.append(Paragraph(f"Finding: {finding.title}", styles['Heading2']))
            if finding.summary:
                story.append(Paragraph(f"Summary: {finding.summary}", styles['Normal']))
            story.append(Spacer(1, 6))
            
            claims = db.query(Claim).filter(Claim.finding_id == finding.id).all()
            for claim in claims:
                story.append(Paragraph(f"Claim: {claim.statement}", styles['Bullet']))
                evidences = db.query(Evidence).filter(Evidence.claim_id == claim.id).all()
                for ev in evidences:
                    doc_name = ev.chunk.document.name if ev.chunk and ev.chunk.document else "Unknown Document"
                    story.append(Paragraph(f"Source Document: {doc_name}", styles['Normal']))
                    if ev.snippet:
                        story.append(Paragraph(f"Evidence: \"{ev.snippet}\"", styles['Italic']))
            story.append(Spacer(1, 12))
            
    doc.build(story)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=flowdocs_report_{str(run_id)[:8]}.pdf"}
    )

import os
from fastapi.responses import FileResponse

@router.get(
    "/{run_id}/documents/{doc_id}/content",
    summary="Stream raw document content to the browser",
)
def get_document_content(
    run_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: Session = Depends(get_db_session),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.run_id == run_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    source_path = doc.metadata_json.get("source")
    if not source_path or not os.path.exists(source_path):
        raise HTTPException(status_code=404, detail="Source file missing on disk")
        
    return FileResponse(source_path)
@router.post(
    "/crash",
    summary="DEV ONLY: Hard crash the server to test recovery",
)
def crash_server():
    """Hard crash the uvicorn process without cleanup."""
    import os
    print("[DEV] Crashing server on purpose!")
    os._exit(1)
