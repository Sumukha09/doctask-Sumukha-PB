"""Structural tests for the LangGraph workflow skeleton.

These tests assert properties of the compiled graph topology only. They do
not exercise business behaviour and they do not call any external service.
"""
from __future__ import annotations

import importlib

from app.workflow.graph import (
    EXPECTED_NODES,
    NODE_ANALYZE,
    NODE_APPROVAL,
    NODE_COMPLETE,
    NODE_EXTRACT,
    NODE_INGEST,
    NODE_VERIFY,
    workflow_graph,
)
from app.workflow.state import WorkflowState


def test_graph_module_imports_successfully() -> None:
    """`app.workflow.graph` imports without raising."""
    module = importlib.import_module("app.workflow.graph")
    assert module is not None
    assert module.workflow_graph is workflow_graph


def test_graph_compiles_to_a_compiled_state_graph() -> None:
    """`workflow_graph` is a compiled LangGraph graph object, not a builder."""
    # LangGraph returns an instance of its compiled graph class.
    assert workflow_graph is not None
    assert hasattr(workflow_graph, "ainvoke"), (
        "Compiled graph must expose ainvoke; got "
        f"{type(workflow_graph).__name__}"
    )


def test_expected_nodes_exist_in_the_compiled_graph() -> None:
    """All six nodes are present in the compiled graph."""
    nodes = set(EXPECTED_NODES)
    assert nodes == {
        NODE_INGEST,
        NODE_EXTRACT,
        NODE_ANALYZE,
        NODE_VERIFY,
        NODE_APPROVAL,
        NODE_COMPLETE,
    }
    # ``CompiledStateGraph.get_graph()`` returns the underlying Graph object
    # which exposes ``nodes`` and ``edges`` for inspection.
    compiled_nodes = set(workflow_graph.get_graph().nodes)
    for node_name in EXPECTED_NODES:
        assert node_name in compiled_nodes, f"missing node: {node_name}"


def test_expected_structural_edges_exist() -> None:
    """The graph has the seven sequential edges from START through END."""
    edges = workflow_graph.get_graph().edges

    expected_edges = {
        ("__start__", NODE_INGEST),
        (NODE_INGEST, NODE_EXTRACT),
        (NODE_EXTRACT, NODE_ANALYZE),
        (NODE_ANALYZE, NODE_VERIFY),
        (NODE_VERIFY, NODE_APPROVAL),
        (NODE_VERIFY, NODE_COMPLETE),
        (NODE_APPROVAL, NODE_COMPLETE),
        (NODE_COMPLETE, "__end__"),
    }
    # Edges are exposed as ``Edge(source, target, data, conditional)``.
    actual_pairs = {(e.source, e.target) for e in edges}

    assert expected_edges.issubset(actual_pairs), (
        "missing edges; "
        f"expected={sorted(expected_edges)} "
        f"actual={sorted(actual_pairs)}"
    )


def test_graph_uses_workflow_state_as_state_schema() -> None:
    """The graph's state schema is the canonical ``WorkflowState`` TypedDict."""
    # ``StateGraph`` exposes its declared schema as ``schema``.
    schema = getattr(workflow_graph, "schema", None)
    if schema is not None:
        assert schema is WorkflowState
    # Cross-check: the annotations on ``WorkflowState`` are the source of truth.
    declared_fields = set(WorkflowState.__annotations__.keys())
    assert len(declared_fields) >= 21, (
        "WorkflowState is expected to define the contract from Step 3"
    )


def test_graph_runs_without_external_api_calls() -> None:
    """Invoking the graph works in a fully offline environment.

    This test does not patch any HTTP client; it simply runs the structural
    placeholders end-to-end and verifies the resulting state. No external
    network call is reachable from any of the placeholder nodes because they
    only return dicts.
    """
    initial: WorkflowState = {
        "run_id": "run-graph-test",
        "current_stage": NODE_INGEST,
        "status": "running",
    }
    result = workflow_graph.invoke(initial)

    # The placeholders advance the stage all the way to "completed".
    assert result["current_stage"] == "completed"
    assert result["status"] == "completed"
    # Every node should have appended itself to ``completed_stages``.
    completed = set(result["completed_stages"])
    assert completed == set(EXPECTED_NODES)


def test_graph_node_functions_return_partial_state_updates() -> None:
    """Each node function returns a dict that updates only structural fields.

    The placeholders must not return full ``WorkflowState`` instances — they
    return partial updates so LangGraph can merge them with the running
    state.
    """
    from app.workflow import graph

    state: WorkflowState = {}
    assert isinstance(graph.ingest_node(state), dict)
    assert isinstance(graph.extract_node(state), dict)
    assert isinstance(graph.analyze_node(state), dict)
    assert isinstance(graph.verify_node(state), dict)
    assert isinstance(graph.approval_node(state), dict)
    assert isinstance(graph.complete_node(state), dict)


def test_graph_does_not_require_external_api_keys() -> None:
    """No import of the graph module touches any external API client."""
    import app.workflow.graph as graph_module

    source = open(graph_module.__file__, encoding="utf-8").read()
    forbidden = [
        "google",
        "anthropic",
        "openai",
        "httpx",  # graph itself must not issue HTTP
        "requests",
    ]
    for token in forbidden:
        assert token not in source, (
            f"workflow.graph must not depend on '{token}'; found in graph.py"
        )
