"""Request and response schemas for runs."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class FileInput(BaseModel):
    file_path: str | None = Field(None, description="Absolute or relative path to the file to process.")
    file_content_base64: str | None = Field(None, description="Base64 encoded file content. If provided, file_path is ignored.")
    file_name: str | None = Field(None, description="Name of the file if uploading via base64.")

class RunCreateRequest(BaseModel):
    """Payload to start a new document processing run."""
    files: list[FileInput] = Field(default_factory=list, description="List of files to process.")
    compliance_rules: str | None = Field(None, description="Custom compliance rules or playbook for the analysis.")


class RunResponse(BaseModel):
    """Standard representation of a run."""
    id: uuid.UUID = Field(..., description="The unique identifier for the run.")
    status: str = Field(..., description="Current status (e.g. pending, running, failed).")
    
    class Config:
        from_attributes = True


class RunStateResponse(BaseModel):
    """The workflow state representation for a run."""
    run_id: uuid.UUID = Field(..., description="The unique identifier for the run.")
    current_stage: str = Field(..., description="The current active stage in the graph.")
    status: str | None = Field(default=None, description="The workflow execution status.")
    completed_stages: list[str] = Field(default_factory=list, description="Stages that have successfully completed.")
    errors: list[str] | None = Field(default=None, description="Any errors encountered.")
    document_ids: list[str] | None = Field(default=None, description="IDs of processed documents.")
    ingested_document_ids: list[str] | None = Field(default=None, description="IDs of successfully ingested documents.")


class EvidenceDetail(BaseModel):
    id: uuid.UUID
    snippet: str | None = None
    relevance: float | None = None
    document_name: str | None = None

    class Config:
        from_attributes = True

class ClaimDetail(BaseModel):
    id: uuid.UUID
    statement: str
    confidence: float | None = None
    evidence: list[EvidenceDetail] = Field(default_factory=list)

    class Config:
        from_attributes = True

class FindingDetail(BaseModel):
    id: uuid.UUID
    title: str
    summary: str | None = None
    severity: str | None = None
    status: str
    claims: list[ClaimDetail] = Field(default_factory=list)

    class Config:
        from_attributes = True

class DocumentDetail(BaseModel):
    id: uuid.UUID
    name: str
    byte_size: int | None = None

    class Config:
        from_attributes = True

class RunDetailsResponse(BaseModel):
    run_id: uuid.UUID
    documents: list[DocumentDetail] = Field(default_factory=list)
    findings: list[FindingDetail] = Field(default_factory=list)

class RunStatsResponse(BaseModel):
    total_runs: int = 0
    active_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_documents: int = 0
    total_claims: int = 0
    total_findings: int = 0
    pending_approvals: int = 0
    total_cost_micro: int = 0

class AuditLogResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    actor: str
    action: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    payload: dict | None = None
    created_at: Any

    class Config:
        from_attributes = True

class CostReportResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    total_cost_micro: int
    currency: str
    breakdown: dict | None = None
    created_at: Any

    class Config:
        from_attributes = True
