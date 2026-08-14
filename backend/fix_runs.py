import sys
import os



from app.db.session import get_session_factory
from app.models.run import Run
from langgraph.checkpoint.postgres import PostgresSaver
from app.workflow.graph import compile_workflow
from app.config import get_settings

def fix_runs():
    session_factory = get_session_factory()
    settings = get_settings()
    conn_string = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    
    with session_factory() as session:
        runs = session.query(Run).filter(Run.status == 'running').all()
        if not runs:
            print("No running runs found.")
            return
            
        with PostgresSaver.from_conn_string(conn_string) as saver:
            graph = compile_workflow(checkpointer=saver, interrupt_before=["approval"])
            
            for run in runs:
                thread_config = {"configurable": {"thread_id": str(run.id)}}
                state_snapshot = graph.get_state(thread_config)
                
                if state_snapshot and state_snapshot.values:
                    state_status = state_snapshot.values.get("status")
                    current_stage = state_snapshot.values.get("current_stage")
                    
                    if state_status == "failed" or current_stage == "failed":
                        run.status = "failed"
                        print(f"Fixed run {run.id} to failed.")
                    elif current_stage == "completed":
                        run.status = "completed"
                        print(f"Fixed run {run.id} to completed.")
                    
        session.commit()
        print("Database sync complete. Old runs are now fixed.")

if __name__ == "__main__":
    fix_runs()
