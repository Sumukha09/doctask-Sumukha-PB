import pytest
import sys
from app.db.session import get_session_factory
from app.models.run import Run
from app.models.audit_log import AuditLog

def test_investigate_db():
    session_factory = get_session_factory()
    with session_factory() as session:
        runs = session.query(Run).order_by(Run.created_at.desc()).limit(1).all()
        if not runs:
            print("\n>>> NO RUNS FOUND")
            assert False
            
        run = runs[0]
        print(f"\n>>> LATEST RUN ID: {run.id}")
        
        logs = session.query(AuditLog).filter(AuditLog.run_id == run.id).all()
        for log in logs:
            if "analyze" in log.action.lower() or "llm" in log.action.lower():
                print(f">>> LOG ACTION: {log.action}, PAYLOAD: {log.payload}")
            
        assert False
