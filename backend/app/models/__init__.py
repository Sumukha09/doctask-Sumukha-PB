"""SQLAlchemy ORM models.

Every model is imported here so that Alembic's autogenerate walks the
complete set of tables through ``Base.metadata``. The side-effect import is
the only thing the package does — it must not contain business logic.
"""

from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.checkpoint import Checkpoint
from app.models.claim import Claim
from app.models.claim_evidence import ClaimEvidence
from app.models.cost_report import CostReport
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.finding import Finding
from app.models.run import Run

__all__ = [
    "Approval",
    "AuditLog",
    "Checkpoint",
    "Claim",
    "ClaimEvidence",
    "CostReport",
    "Document",
    "DocumentChunk",
    "Finding",
    "Run",
]
