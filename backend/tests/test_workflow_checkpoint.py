"""Tests for LangGraph checkpoint persistence."""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest
from langgraph.checkpoint.postgres import PostgresSaver

from app.config import Settings
from app.db.session import get_session_factory
from app.models import Run
from app.workflow.graph import compile_workflow


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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"Test durable execution document.")
        f_path = f.name
    
    yield f_path
    
    if os.path.exists(f_path):
        os.remove(f_path)


@pytest.fixture
def checkpointer():
    """Provides a configured checkpointer connected to the test DB."""
    # Convert sqlalchemy URL to psycopg3 URL
    conn_string = Settings().database_url
    conn_string = conn_string.replace("postgresql+psycopg://", "postgresql://")
    
    with PostgresSaver.from_conn_string(conn_string) as saver:
        saver.setup()
        yield saver


def test_checkpoint_persistence_and_resume(db_session, temp_document, checkpointer) -> None:
    """Test that a workflow can be paused, persisted, and resumed."""
    # 1. Setup a valid run and file so ingest_node passes
    run = Run(status="pending", input_metadata={"file_path": temp_document})
    db_session.add(run)
    db_session.commit()
    
    run_id = str(run.id)
    thread_config = {"configurable": {"thread_id": run_id}}
    
    # 2. Compile graph to pause BEFORE verify
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["verify"])
    
    # 3. Initial invocation
    initial_state = {
        "run_id": run_id,
        "current_stage": "ingest",
        "completed_stages": []
    }
    
    # Run the graph; it should stop before 'verify'
    result = graph.invoke(initial_state, config=thread_config)
    
    # Verify it stopped where we expect
    assert result["current_stage"] == "verify"
    assert "ingest" in result["completed_stages"]
    assert "extract" in result["completed_stages"]
    assert "analyze" in result["completed_stages"]
    
    # 4. Verify checkpointer state directly
    saved_state = graph.get_state(thread_config)
    assert saved_state is not None
    assert saved_state.values["current_stage"] == "verify"
    
    # 5. Simulate a process restart by creating a brand new graph instance
    new_graph = compile_workflow(checkpointer=checkpointer, interrupt_before=[])
    
    # 6. Resume from the checkpoint using ONLY the config with the thread_id
    # We pass None for state to let it load from the checkpointer
    final_result = new_graph.invoke(None, config=thread_config)
    
    # Verify it ran to completion
    assert final_result["current_stage"] == "completed"
    assert "verify" in final_result["completed_stages"]
    assert "approval" in final_result["completed_stages"]
    assert "complete" in final_result["completed_stages"]


def test_thread_isolation(db_session, temp_document, checkpointer) -> None:
    """Test that separate runs have independent checkpoint states."""
    # Create two separate runs
    run1 = Run(status="pending", input_metadata={"file_path": temp_document})
    run2 = Run(status="pending", input_metadata={"file_path": temp_document})
    db_session.add_all([run1, run2])
    db_session.commit()
    
    config1 = {"configurable": {"thread_id": str(run1.id)}}
    config2 = {"configurable": {"thread_id": str(run2.id)}}
    
    graph = compile_workflow(checkpointer=checkpointer, interrupt_before=["extract"])
    
    # Run thread 1
    graph.invoke({"run_id": str(run1.id)}, config=config1)
    
    # Thread 1 should be at extract, Thread 2 should have no state
    state1 = graph.get_state(config1)
    state2 = graph.get_state(config2)
    
    assert state1 is not None
    assert state1.values["current_stage"] == "extract"
    # State2 has never been invoked, so its values dict should be empty or default
    assert not state2.values
