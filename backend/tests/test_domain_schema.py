"""Schema-level tests for the Step 2 domain model.

These tests assume migrations have already been applied (the suite runs
against the same database Alembic writes to). They verify the schema is the
shape the application expects.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models import (
    Approval,
    AuditLog,
    Checkpoint,
    Claim,
    ClaimEvidence,
    CostReport,
    Document,
    DocumentChunk,
    Finding,
    Run,
)

REQUIRED_TABLES = {
    "runs",
    "checkpoints",
    "documents",
    "document_chunks",
    "findings",
    "claims",
    "claim_evidence",
    "approvals",
    "cost_reports",
    "audit_logs",
}


def test_required_tables_exist() -> None:
    """Every table required by the domain model is present in the schema."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        ).fetchall()
    actual = {row[0] for row in rows}
    missing = REQUIRED_TABLES - actual
    assert not missing, f"Missing tables: {sorted(missing)}"


def test_documents_hash_has_unique_constraint() -> None:
    """`documents.hash` is uniquely constrained at the database level."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'documents'::regclass AND contype = 'u'"
            )
        ).fetchall()
    constraint_names = {row[0] for row in rows}
    assert "uq_documents_hash" in constraint_names


def test_documents_hash_unique_constraint_is_enforced() -> None:
    """Inserting two documents with the same hash fails with IntegrityError."""
    session_factory = get_engine()  # noqa: F841 — used by the Session binding below.
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        run = Run(status="created")
        session.add(run)
        session.flush()

        session.add(
            Document(
                run_id=run.id,
                hash="dup-hash-1",
                name="first",
                mime_type="text/plain",
                byte_size=10,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    session = factory()
    try:
        run_id = session.execute(
            text("SELECT id FROM documents WHERE hash = :h"),
            {"h": "dup-hash-1"},
        ).scalar_one()

        duplicate = Document(
            run_id=run_id,
            hash="dup-hash-1",
            name="second",
        )
        session.add(duplicate)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            assert "uq_documents_hash" in str(exc).lower() or "unique" in str(exc).lower()
        else:
            raise AssertionError(
                "Expected a unique-constraint violation on documents.hash; "
                "the row was inserted without error."
            )
    finally:
        # Clean up so this test does not leave rows behind.
        session.execute(
            text("DELETE FROM documents WHERE hash = :h"), {"h": "dup-hash-1"}
        )
        session.commit()
        session.close()


def test_pgvector_column_dimension() -> None:
    """The `embedding` column on `document_chunks` is a vector(1536)."""
    engine = get_engine()
    with engine.connect() as conn:
        dim = conn.execute(
            text(
                "SELECT atttypmod FROM pg_attribute "
                "JOIN pg_class c ON c.oid = attrelid "
                "WHERE c.relname = 'document_chunks' AND attname = 'embedding'"
            )
        ).scalar_one()
    assert dim == 1536


def test_foreign_keys_cascade_on_run_delete() -> None:
    """Deleting a run cascades through every dependent table."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session = factory()
    try:
        run = Run(status="created")
        session.add(run)
        session.flush()

        session.add(
            Checkpoint(
                run_id=run.id,
                step="test",
                payload={"k": "v"},
            )
        )
        session.add(
            Document(
                run_id=run.id,
                hash="cascade-hash",
                name="x",
            )
        )
        session.commit()

        run_id = run.id
        children_before = (
            session.query(Checkpoint).filter_by(run_id=run_id).count(),
            session.query(Document).filter_by(run_id=run_id).count(),
        )
        assert children_before == (1, 1)

        # Delete the run; cascade should wipe children.
        session.delete(run)
        session.commit()

        assert session.query(Run).filter_by(id=run_id).count() == 0
        assert session.query(Checkpoint).filter_by(run_id=run_id).count() == 0
        assert session.query(Document).filter_by(run_id=run_id).count() == 0
    finally:
        session.close()


def test_run_to_evidence_relationship_round_trip() -> None:
    """A complete Run → Document → Chunk → Finding → Claim → Evidence graph persists and reloads."""
    from decimal import Decimal

    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        run = Run(
            status="created",
            trigger_source="unit-test",
            input_metadata={"source": "tests"},
        )
        document = Document(
            run=run,
            hash="round-trip-hash",
            name="doc.txt",
            mime_type="text/plain",
            byte_size=42,
            metadata_json={"lang": "en"},
        )
        chunk = DocumentChunk(
            document=document,
            run=run,
            chunk_index=0,
            text="the quick brown fox jumps over the lazy dog",
            embedding=[0.01] * 1536,
            token_count=9,
        )
        finding = Finding(
            run=run,
            title="Observation",
            summary="Noted something",
            severity="info",
            status="open",
            payload={"confidence": 0.9},
        )
        claim = Claim(
            finding=finding,
            run=run,
            statement="A fox jumped over a dog.",
            confidence=0.95,
        )
        evidence = ClaimEvidence(
            claim=claim,
            chunk=chunk,
            relevance=0.85,
            snippet="...the quick brown fox...",
        )

        session.add_all([run])
        session.commit()

        # Reload the graph in a fresh state to ensure everything is flushable.
        session.expire_all()
        loaded = session.get(Run, run.id)
        assert loaded is not None
        assert loaded.status == "created"
        assert loaded.input_metadata == {"source": "tests"}

        assert len(loaded.documents) == 1
        loaded_document = loaded.documents[0]
        assert loaded_document.hash == "round-trip-hash"
        assert loaded_document.metadata_json == {"lang": "en"}
        assert len(loaded_document.chunks) == 1

        loaded_chunk = loaded_document.chunks[0]
        assert loaded_chunk.text.startswith("the quick brown fox")
        assert loaded_chunk.embedding is not None
        assert len(loaded_chunk.embedding) == 1536

        assert len(loaded.findings) == 1
        loaded_finding = loaded.findings[0]
        assert loaded_finding.payload == {"confidence": 0.9}
        assert len(loaded_finding.claims) == 1

        loaded_claim = loaded_finding.claims[0]
        assert loaded_claim.confidence == Decimal("0.9500")
        assert len(loaded_claim.evidence) == 1

        loaded_evidence = loaded_claim.evidence[0]
        assert loaded_evidence.relevance == Decimal("0.8500")
        assert loaded_evidence.chunk_id == loaded_chunk.id

        # Persist timestamps prove the column is a real timestamptz.
        assert loaded.created_at.tzinfo is not None
        assert loaded_document.created_at.tzinfo is not None
        assert loaded_finding.created_at.tzinfo is not None
        assert loaded_claim.created_at.tzinfo is not None

        # Test ordering on the chunks relationship.
        assert loaded_document.chunks[0].chunk_index == 0
    finally:
        session.close()
        # Clean up; cascade takes care of the whole graph.
        session = factory()
        try:
            session.execute(
                text(
                    "DELETE FROM documents WHERE hash = :h"
                ),
                {"h": "round-trip-hash"},
            )
            session.commit()
        finally:
            session.close()


def test_jsonb_round_trip() -> None:
    """JSONB columns persist and retrieve arbitrary structured data."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        payload = {
            "list": [1, 2, 3],
            "nested": {"k": "v", "n": None, "b": True},
        }
        run = Run(status="created", input_metadata=payload)
        session.add(run)
        session.commit()

        session.expire_all()
        loaded = session.get(Run, run.id)
        assert loaded is not None
        assert loaded.input_metadata == payload
    finally:
        session.close()
        session = factory()
        try:
            session.execute(
                text(
                    "DELETE FROM runs WHERE status = 'created' AND input_metadata = CAST(:p AS jsonb)"
                ),
                {"p": '{"list": [1, 2, 3], "nested": {"k": "v", "n": null, "b": true}}'},
            )
            session.commit()
        finally:
            session.close()


def test_claim_evidence_uniqueness_per_pair() -> None:
    """The same chunk cannot be attached twice to the same claim."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        run = Run(status="created")
        document = Document(run=run, hash="uniq-pair-hash", name="d")
        chunk = DocumentChunk(document=document, run=run, chunk_index=0, text="x")
        finding = Finding(run=run, title="t", status="open")
        claim = Claim(finding=finding, run=run, statement="s")
        session.add(run)
        session.flush()

        session.add(ClaimEvidence(claim=claim, chunk=chunk, relevance=0.5))
        session.commit()

        dup = ClaimEvidence(claim=claim, chunk=chunk, relevance=0.7)
        session.add(dup)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            assert (
                "uq_claim_evidence_claim_chunk" in str(exc).lower()
                or "unique" in str(exc).lower()
            )
        else:
            raise AssertionError(
                "Expected a unique-constraint violation on claim_evidence pair; "
                "the duplicate row was inserted."
            )
    finally:
        session.close()
        session = factory()
        try:
            session.execute(
                text("DELETE FROM documents WHERE hash = :h"),
                {"h": "uniq-pair-hash"},
            )
            session.commit()
        finally:
            session.close()


def test_cost_report_unique_per_run() -> None:
    """A run can only have one cost report."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        run = Run(status="created")
        session.add(run)
        session.flush()

        session.add(
            CostReport(
                run_id=run.id,
                total_cost_micro=1000,
                currency="USD",
                breakdown={"llm": 700},
            )
        )
        session.commit()

        dup = CostReport(
            run_id=run.id,
            total_cost_micro=2000,
            currency="USD",
        )
        session.add(dup)
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            assert (
                "uq_cost_reports_run_id" in str(exc).lower()
                or "unique" in str(exc).lower()
            )
        else:
            raise AssertionError(
                "Expected a unique-constraint violation on cost_reports.run_id."
            )
    finally:
        session.close()
        session = factory()
        try:
            session.execute(
                text(
                    "DELETE FROM cost_reports WHERE run_id IN ("
                    "  SELECT id FROM runs WHERE status = 'created'"
                    ")"
                )
            )
            session.execute(
                text("DELETE FROM runs WHERE status = 'created'")
            )
            session.commit()
        finally:
            session.close()


def test_audit_log_payload_round_trip() -> None:
    """An audit log entry round-trips its JSONB payload."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    session: Session = factory()
    try:
        run = Run(status="created")
        session.add(run)
        session.flush()

        log = AuditLog(
            run_id=run.id,
            actor="test",
            action="create",
            payload={"event": "started", "level": 1},
        )
        session.add(log)
        session.commit()

        session.expire_all()
        loaded = session.get(AuditLog, log.id)
        assert loaded is not None
        assert loaded.payload == {"event": "started", "level": 1}
    finally:
        session.close()
        session = factory()
        try:
            session.execute(
                text(
                    "DELETE FROM audit_logs WHERE actor = 'test' AND action = 'create'"
                )
            )
            session.execute(
                text("DELETE FROM runs WHERE status = 'created'")
            )
            session.commit()
        finally:
            session.close()
