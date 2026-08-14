"""Validation tests for the WorkflowState contract.

These tests assert structural and serialisation properties of the canonical
state. They do **not** import any workflow runtime, LangGraph objects, or
SQLAlchemy sessions; the contract is meant to be free of those concerns.
"""
from __future__ import annotations

import json
from typing import get_type_hints

import pytest

from app.workflow.state import (
    WORKFLOW_STATE_FIELDS,
    ApprovalDecision,
    Stage,
    Status,
    WorkflowState,
)

# ---------------------------------------------------------------------------
# Field set — the canonical list of keys the spec mandates.
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: dict[str, object] = {
    # Lifecycle
    "run_id": str,
    "current_stage": str,
    "status": str,
    "document_ids": list[str],
    "completed_stages": list[str],
    "errors": list[str],
    # Approval
    "approval_required": bool,
    "approval_decision": str | None,
    "rejection_reason": str | None,
    "reviewer": str | None,
    # Ingest
    "chunk_ids": list[str],
    "chunk_count": int,
    "ingested_document_ids": list[str],
    # Extract
    "extracted_claim_ids": list[str],
    "extracted_entity_count": int,
    "processed_chunk_ids": list[str],
    # Analyze
    "analyzed_finding_ids": list[str],
    "analyzed_claim_ids": list[str],
    # Verify
    "verified_claim_ids": list[str],
    "verification_result_counts": dict[str, int],
    "failed_insufficient_evidence_count": int,
}


def _state_with_all_fields() -> WorkflowState:
    """Build a fully-populated, valid state object for round-trip tests."""
    return WorkflowState(
        run_id="run-1",
        current_stage="ingest",
        status="running",
        document_ids=["doc-1", "doc-2"],
        completed_stages=[],
        errors=[],
        approval_required=False,
        approval_decision=None,
        rejection_reason=None,
        reviewer=None,
        chunk_ids=[],
        chunk_count=0,
        ingested_document_ids=[],
        extracted_claim_ids=[],
        extracted_entity_count=0,
        processed_chunk_ids=[],
        analyzed_finding_ids=[],
        analyzed_claim_ids=[],
        verified_claim_ids=[],
        verification_result_counts={"verified": 0, "rejected": 0, "insufficient": 0},
        failed_insufficient_evidence_count=0,
    )


# ---------------------------------------------------------------------------
# Shape tests
# ---------------------------------------------------------------------------


def test_state_has_exactly_the_required_fields() -> None:
    """The TypedDict defines exactly the 21 fields specified by the contract."""
    actual = set(WorkflowState.__annotations__.keys())
    expected = set(REQUIRED_FIELDS.keys())
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"Missing fields: {sorted(missing)}"
    assert not extra, f"Unexpected fields: {sorted(extra)}"
    assert len(actual) == 21


def test_state_field_constants_match_typeddict() -> None:
    """The exported ``WORKFLOW_STATE_FIELDS`` reflects the TypedDict annotations."""
    assert WORKFLOW_STATE_FIELDS == frozenset(REQUIRED_FIELDS.keys())
    assert len(WORKFLOW_STATE_FIELDS) == 21


def test_total_false_makes_all_fields_optional() -> None:
    """An empty state is a valid WorkflowState instance."""
    empty: WorkflowState = WorkflowState()
    # The dict is empty and still satisfies the contract.
    assert dict(empty) == {}


# ---------------------------------------------------------------------------
# Type-annotation tests
# ---------------------------------------------------------------------------


def test_field_types_match_spec() -> None:
    """Each field is annotated with the type the spec requires."""
    hints = get_type_hints(WorkflowState)
    for name, expected in REQUIRED_FIELDS.items():
        assert name in hints, f"{name} is not annotated on WorkflowState"
        assert hints[name] == expected, (
            f"{name}: expected {expected!r}, got {hints[name]!r}"
        )


# ---------------------------------------------------------------------------
# Serialisation tests
# ---------------------------------------------------------------------------


def test_full_state_round_trips_through_json() -> None:
    """A complete state serialises to JSON and back without loss."""
    state = _state_with_all_fields()
    payload = json.dumps(state)
    reloaded = json.loads(payload)
    assert reloaded == dict(state)


def test_partial_state_round_trips_through_json() -> None:
    """A partial state (only some fields populated) serialises cleanly."""
    state: WorkflowState = WorkflowState(
        run_id="run-partial",
        current_stage="extract",
        status="running",
    )
    payload = json.dumps(state)
    reloaded = json.loads(payload)
    assert reloaded == {
        "run_id": "run-partial",
        "current_stage": "extract",
        "status": "running",
    }


def test_list_fields_accept_string_identifiers() -> None:
    """Document/chunk/claim/finding id lists hold plain string identifiers."""
    state: WorkflowState = _state_with_all_fields()
    state["document_ids"] = ["doc-a", "doc-b"]
    state["chunk_ids"] = ["chunk-1"]
    state["extracted_claim_ids"] = ["claim-1", "claim-2"]
    payload = json.dumps(state)
    reloaded = json.loads(payload)
    assert reloaded["document_ids"] == ["doc-a", "doc-b"]
    assert reloaded["chunk_ids"] == ["chunk-1"]
    assert reloaded["extracted_claim_ids"] == ["claim-1", "claim-2"]


def test_verification_result_counts_round_trips() -> None:
    """`verification_result_counts` is a JSONB-friendly dict[str, int]."""
    state: WorkflowState = _state_with_all_fields()
    state["verification_result_counts"] = {
        "verified": 12,
        "rejected": 1,
        "insufficient": 2,
    }
    payload = json.dumps(state)
    reloaded = json.loads(payload)
    assert reloaded["verification_result_counts"] == {
        "verified": 12,
        "rejected": 1,
        "insufficient": 2,
    }


# ---------------------------------------------------------------------------
# Approval-field tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("decision", "reason", "reviewer"),
    [
        ("approved", None, "alice"),
        ("rejected", "Missing source citation for claim 3", "bob"),
        (None, None, None),
    ],
)
def test_approval_fields_round_trip(
    decision: str | None, reason: str | None, reviewer: str | None
) -> None:
    """Approval metadata serialises through JSON losslessly."""
    state: WorkflowState = _state_with_all_fields()
    state["approval_required"] = decision is not None
    state["approval_decision"] = decision
    state["rejection_reason"] = reason
    state["reviewer"] = reviewer

    payload = json.dumps(state)
    reloaded = json.loads(payload)

    assert reloaded["approval_required"] is (decision is not None)
    assert reloaded["approval_decision"] == decision
    assert reloaded["rejection_reason"] == reason
    assert reloaded["reviewer"] == reviewer


# ---------------------------------------------------------------------------
# Forbidden-content tests — the contract must remain free of runtime objects.
# ---------------------------------------------------------------------------


def test_state_module_does_not_import_runtime_layers() -> None:
    """The state module must not pull in SQLAlchemy, LangGraph, or LLM clients."""
    import app.workflow.state as state_module

    source = open(state_module.__file__, encoding="utf-8").read()
    forbidden = [
        "sqlalchemy",
        "langgraph",
        "google",
        "anthropic",
        "openai",
        "genai",
        "Session",  # SQLAlchemy session class
        "engine",  # SQLAlchemy engine
    ]
    for token in forbidden:
        assert token not in source, (
            f"WorkflowState must not depend on '{token}'; found in state.py"
        )


def test_state_does_not_hold_bytes_or_file_objects() -> None:
    """A canonical state never carries file bytes or document text."""
    state: WorkflowState = _state_with_all_fields()
    payload = json.dumps(state)
    reloaded = json.loads(payload)
    for value in reloaded.values():
        assert not isinstance(value, (bytes, bytearray))
    # No field carries document text. Spec puts text on document_chunks in the
    # database, never on the state.
    assert "text" not in reloaded
    assert "content" not in reloaded
    assert "bytes" not in reloaded


def test_state_serialisable_with_only_builtin_types() -> None:
    """Every value in a populated state is a JSON-serialisable builtin."""
    state: WorkflowState = _state_with_all_fields()
    # If any value cannot be serialised, json.dumps will raise.
    json.dumps(state)


# ---------------------------------------------------------------------------
# Vocabulary literal tests — these guard against typos in stage/status names.
# ---------------------------------------------------------------------------


def test_stage_literal_contains_expected_stages() -> None:
    """The Stage literal lists the pipeline stages."""
    args = set(Stage.__args__)  # type: ignore[attr-defined]
    assert args == {"ingest", "extract", "analyze", "verify", "approve", "finalize"}


def test_status_literal_contains_expected_statuses() -> None:
    """The Status literal lists the run statuses."""
    args = set(Status.__args__)  # type: ignore[attr-defined]
    assert args == {
        "pending",
        "running",
        "awaiting_approval",
        "approved",
        "rejected",
        "failed",
        "completed",
    }


def test_approval_decision_literal_is_two_way() -> None:
    """Only ``approved`` and ``rejected`` are valid decisions."""
    args = set(ApprovalDecision.__args__)  # type: ignore[attr-defined]
    assert args == {"approved", "rejected"}
