"""Step 2 — domain schema.

Creates the ten domain tables for FlowDocs V2:

    runs, checkpoints, documents, document_chunks, findings,
    claims, claim_evidence, approvals, cost_reports, audit_logs

Design notes:

* UUID primary keys are generated client-side (``uuid.uuid4``) so the model
  is portable across PostgreSQL extensions. Server defaults (``now()``) keep
  timestamps stable without requiring application-side clock handling.
* Every timestamp column uses ``TIMESTAMP WITH TIME ZONE`` (TIMESTAMPTZ).
* ``documents.hash`` is uniquely constrained so a duplicate upload within
  the same table is impossible. The constraint is enforced by PostgreSQL.
* ``claim_evidence`` is an explicit junction table so that additional
  per-link attributes (``relevance``, ``snippet``) can be stored and
  per-pair uniqueness can be enforced via ``uq_claim_evidence_claim_chunk``.
* The ``Vector(1536)`` column on ``document_chunks`` is created using the
  pgvector ``VECTOR`` type with a fixed dimension. This matches the
  embedding dimension produced by the configured embedding model.
* Cascading deletes are handled at the database level (``ON DELETE
  CASCADE``) and mirrored at the ORM level so both layers agree.

Revision ID: 0002_domain_schema
Revises: 0001_enable_pgvector
Create Date: 2026-08-11

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_domain_schema"
down_revision: Union[str, None] = "0001_enable_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("trigger_source", sa.String(length=128), nullable=True),
        sa.Column(
            "input_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_status", "runs", ["status"], unique=False)
    op.create_index("ix_runs_created_at", "runs", ["created_at"], unique=False)

    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("payload_ref", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checkpoints_run_id", "checkpoints", ["run_id"], unique=False)
    op.create_index(
        "ix_checkpoints_run_step", "checkpoints", ["run_id", "step"], unique=False
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hash", name="uq_documents_hash"),
    )
    op.create_index("ix_documents_run_id", "documents", ["run_id"], unique=False)
    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_index"
        ),
    )
    op.create_index(
        "ix_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_run_id", "document_chunks", ["run_id"], unique=False
    )

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_findings_run_id", "findings", ["run_id"], unique=False)
    op.create_index("ix_findings_status", "findings", ["status"], unique=False)

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_finding_id", "claims", ["finding_id"], unique=False)
    op.create_index("ix_claims_run_id", "claims", ["run_id"], unique=False)

    op.create_table(
        "claim_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevance", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "relevance IS NULL OR (relevance >= 0 AND relevance <= 1)",
            name="ck_claim_evidence_relevance_range",
        ),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "claim_id", "chunk_id", name="uq_claim_evidence_claim_chunk"
        ),
    )
    op.create_index(
        "ix_claim_evidence_claim_id", "claim_evidence", ["claim_id"], unique=False
    )
    op.create_index(
        "ix_claim_evidence_chunk_id", "claim_evidence", ["chunk_id"], unique=False
    )

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"], unique=False)
    op.create_index("ix_approvals_decision", "approvals", ["decision"], unique=False)

    op.create_table(
        "cost_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_cost_micro", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column(
            "breakdown",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_cost_reports_run_id"),
    )
    op.create_index(
        "ix_cost_reports_created_at", "cost_reports", ["created_at"], unique=False
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_run_id", "audit_logs", ["run_id"], unique=False)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)
    op.create_index(
        "ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False
    )


def downgrade() -> None:
    # Reverse the table creation order to honour foreign-key dependencies.
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_run_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_cost_reports_created_at", table_name="cost_reports")
    op.drop_table("cost_reports")

    op.drop_index("ix_approvals_decision", table_name="approvals")
    op.drop_index("ix_approvals_run_id", table_name="approvals")
    op.drop_table("approvals")

    op.drop_index("ix_claim_evidence_chunk_id", table_name="claim_evidence")
    op.drop_index("ix_claim_evidence_claim_id", table_name="claim_evidence")
    op.drop_table("claim_evidence")

    op.drop_index("ix_claims_run_id", table_name="claims")
    op.drop_index("ix_claims_finding_id", table_name="claims")
    op.drop_table("claims")

    op.drop_index("ix_findings_status", table_name="findings")
    op.drop_index("ix_findings_run_id", table_name="findings")
    op.drop_table("findings")

    op.drop_index("ix_document_chunks_run_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_index("uq_document_chunks_document_index", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_run_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_checkpoints_run_step", table_name="checkpoints")
    op.drop_index("ix_checkpoints_run_id", table_name="checkpoints")
    op.drop_table("checkpoints")

    op.drop_index("ix_runs_created_at", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_table("runs")
