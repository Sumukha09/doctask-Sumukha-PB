import uuid
import os
import threading
from typing import List, Optional

from app.db.session import get_session_factory
from app.api.deps import get_checkpointer
from app.models.run import Run
from app.models.finding import Finding
from app.models.document import Document
from app.api.routes.runs import run_graph_background
from app.workflow.graph import compile_workflow

def _get_run_or_raise(session, run_id: str) -> Run:
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise ValueError(f"Invalid UUID: {run_id}")
    run = session.get(Run, rid)
    if not run:
        raise ValueError(f"Run {run_id} not found.")
    return run

def register_tools(mcp):
    @mcp.tool()
    def create_run(file_paths: List[str], compliance_rules: str = None) -> dict:
        """Create a new document processing run.
        
        Args:
            file_paths: List of absolute file paths to process.
            compliance_rules: Optional rules or playbook.
            
        Returns:
            dict: Initial run state.
        """
        if not file_paths:
            raise ValueError("Must provide at least one valid file_path.")
            
        session_factory = get_session_factory()
        with session_factory() as session:
            run = Run(status="running", input_metadata={
                "file_paths": file_paths,
                "compliance_rules": compliance_rules
            })
            session.add(run)
            session.commit()
            run_id_str = str(run.id)
            
        initial_state = {
            "run_id": run_id_str,
            "current_stage": "ingest",
        }
        
        # Start graph background execution
        threading.Thread(target=run_graph_background, args=(run_id_str, initial_state), daemon=True).start()
        
        return initial_state

    @mcp.tool()
    def get_run(run_id: str) -> dict:
        """Get the basic database status of a run.
        
        Args:
            run_id: The ID of the run.
        """
        session_factory = get_session_factory()
        with session_factory() as session:
            run = _get_run_or_raise(session, run_id)
            return {
                "run_id": str(run.id),
                "status": run.status,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None,
            }

    @mcp.tool()
    def get_run_state(run_id: str) -> dict:
        """Retrieve the durable LangGraph state for a run, showing the execution trace.
        
        Args:
            run_id: The ID of the run.
        """
        checkpointer_gen = get_checkpointer()
        checkpointer = next(checkpointer_gen)
        try:
            graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
            thread_config = {"configurable": {"thread_id": run_id}}
            
            state_snapshot = graph.get_state(thread_config)
            
            if state_snapshot and state_snapshot.values:
                state = dict(state_snapshot.values)
            else:
                state = {"run_id": run_id, "current_stage": "ingest"}
                
            session_factory = get_session_factory()
            with session_factory() as session:
                run = session.get(Run, uuid.UUID(run_id))
                if run:
                    if run.status == "failed":
                        state["status"] = "failed"
                        if run.input_metadata and "error" in run.input_metadata:
                            errors = state.get("errors") or []
                            if run.input_metadata["error"] not in errors:
                                errors.append(run.input_metadata["error"])
                            state["errors"] = errors
                    elif not state.get("status"):
                        state["status"] = run.status
                        
            return state
        finally:
            checkpointer_gen.close()

    @mcp.tool()
    def resume_run(run_id: str) -> dict:
        """Resume a stalled or failed workflow run from its existing checkpoint.
        
        Args:
            run_id: The ID of the run to resume.
        """
        session_factory = get_session_factory()
        with session_factory() as session:
            run = _get_run_or_raise(session, run_id)
            if run.status == "completed":
                raise ValueError(f"Cannot resume a completed run.")
                
            run.status = "running"
            session.commit()
            
        # Start graph background execution from checkpoint (None initial state triggers resume)
        threading.Thread(target=run_graph_background, args=(run_id, None), daemon=True).start()
        
        return {"run_id": run_id, "status": "resumed"}

    @mcp.tool()
    def add_documents(run_id: str, file_paths: List[str]) -> dict:
        """Add new documents to an existing run and selectively process them.
        
        Args:
            run_id: The ID of the run.
            file_paths: List of absolute file paths to add.
        """
        import hashlib
        session_factory = get_session_factory()
        added_docs = []
        
        with session_factory() as session:
            run = _get_run_or_raise(session, run_id)
            
            for path in file_paths:
                if not os.path.exists(path):
                    raise ValueError(f"File not found: {path}")
                
                with open(path, "rb") as f:
                    content = f.read()
                    
                content_hash = hashlib.sha256(content).hexdigest()
                # Check if this exact file is already in the run
                existing_doc = session.query(Document).filter(
                    Document.run_id == run.id,
                    Document.content_hash == content_hash
                ).first()
                
                if not existing_doc:
                    doc = Document(
                        run_id=run.id,
                        name=os.path.basename(path),
                        content_hash=content_hash,
                        byte_size=len(content)
                    )
                    session.add(doc)
                    added_docs.append({"name": doc.name, "path": path, "byte_size": doc.byte_size})
            
            if not added_docs:
                return {"run_id": run_id, "message": "All documents already exist in the run.", "added_documents": []}
                
            run.status = "running"
            meta = dict(run.input_metadata or {})
            existing_paths = meta.get("file_paths", [])
            for doc in added_docs:
                if doc["path"] not in existing_paths:
                    existing_paths.append(doc["path"])
            meta["file_paths"] = existing_paths
            run.input_metadata = meta
            session.commit()
            
        # Resume the workflow so ingest node picks up the new files
        threading.Thread(target=run_graph_background, args=(run_id, None), daemon=True).start()
        
        return {"run_id": run_id, "added_documents": added_docs, "status": "running"}

    @mcp.tool()
    def get_findings(run_id: str) -> List[dict]:
        """Get all persisted compliance findings for a run.
        
        Args:
            run_id: The ID of the run.
        """
        session_factory = get_session_factory()
        with session_factory() as session:
            findings = session.query(Finding).filter(Finding.run_id == uuid.UUID(run_id)).all()
            return [
                {
                    "finding_id": str(f.id),
                    "title": f.title,
                    "summary": f.summary,
                    "severity": f.severity,
                    "status": f.status,
                }
                for f in findings
            ]

    @mcp.tool()
    def review_finding(run_id: str, finding_id: str, decision: str, comment: str = None) -> dict:
        """Perform a human approval action programmatically.
        
        Args:
            run_id: The ID of the run.
            finding_id: The ID of the finding.
            decision: 'approve', 'reject', or 'edit'
            comment: Optional reviewer comment.
        """
        session_factory = get_session_factory()
        with session_factory() as session:
            finding = session.query(Finding).filter(
                Finding.id == uuid.UUID(finding_id), 
                Finding.run_id == uuid.UUID(run_id)
            ).with_for_update().first()
            
            if not finding:
                raise ValueError("Finding not found for this run.")
                
            if finding.status != "pending":
                raise ValueError(f"Finding has already been reviewed (current status: {finding.status}).")
                
            if decision == "approve":
                finding.status = "approved"
            elif decision == "reject":
                finding.status = "rejected"
            else:
                raise ValueError(f"Invalid decision: {decision}. Must be 'approve' or 'reject'.")
                
            session.commit()
            
            pending_count = session.query(Finding).filter(
                Finding.run_id == uuid.UUID(run_id), 
                Finding.status == "pending"
            ).count()
            
        if pending_count == 0:
            # All findings are reviewed! Update the graph state and resume.
            checkpointer_gen = get_checkpointer()
            checkpointer = next(checkpointer_gen)
            try:
                graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["approval"])
                thread_config = {"configurable": {"thread_id": run_id}}
                
                graph.update_state(
                    thread_config,
                    {"approval_decision": "approved", "reviewer": "mcp_machine"},
                    as_node="verify"
                )
                
                threading.Thread(target=run_graph_background, args=(run_id, None), daemon=True).start()
                return {"finding_id": finding_id, "status": finding.status, "message": "All findings reviewed, workflow resumed."}
            finally:
                checkpointer_gen.close()
            
        return {"finding_id": finding_id, "status": finding.status, "message": f"{pending_count} findings remaining."}

    @mcp.tool()
    def get_report(run_id: str) -> dict:
        """Retrieve the generated report metadata.
        
        Args:
            run_id: The ID of the run.
        """
        session_factory = get_session_factory()
        with session_factory() as session:
            run = _get_run_or_raise(session, run_id)
            meta = dict(run.input_metadata or {})
            report_meta = meta.get("report_metadata", {})
            
            if not report_meta:
                return {"status": "unavailable", "message": "Report not yet generated for this run."}
                
            return {
                "status": "available",
                "report_metadata": report_meta
            }
