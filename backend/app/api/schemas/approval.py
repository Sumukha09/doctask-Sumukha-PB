"""Request schemas for finding approval."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """Payload to review a single finding."""
    decision: Literal["approve", "reject", "edit"] = Field(
        ..., 
        description="The human reviewer's decision."
    )
    comment: str | None = Field(
        default=None, 
        description="Optional justification or context for the decision."
    )
    edited_text: str | None = Field(
        default=None, 
        description="The corrected finding summary if the decision is 'edit'."
    )
    
    # Validations
    def model_post_init(self, __context):
        if self.decision == "edit" and not self.edited_text:
            raise ValueError("edited_text is required when decision is 'edit'")
