"""Request and Response schemas for the LLM Adapter."""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    """A canonical request to the LLM adapter."""
    
    system_prompt: str = Field(..., description="System instructions for the LLM.")
    user_prompt: str = Field(..., description="The main query or data to process.")
    
    # Optional schema to force structured output
    response_schema: Type[BaseModel] | None = Field(
        default=None, 
        description="Pydantic model class for structured JSON output."
    )
    max_output_tokens: int | None = Field(
        default=None,
        description="Maximum tokens allowed in the response."
    )

    # Observability fields
    request_id: str | None = Field(default=None, description="Unique ID for this logical request.")
    run_id: str | None = Field(default=None, description="The workflow run ID this request belongs to.")
    node: str | None = Field(default=None, description="The graph node making this request.")
    purpose: str | None = Field(default=None, description="What the request is trying to achieve.")


class LLMResponse(BaseModel):
    """A canonical response from the LLM adapter."""
    
    content: str = Field(..., description="Raw text response from the model.")
    parsed_content: Any | None = Field(
        default=None, 
        description="Hydrated BaseModel instance if a response_schema was requested."
    )
    
    input_tokens: int = Field(default=0, description="Tokens consumed in the prompt.")
    output_tokens: int = Field(default=0, description="Tokens generated in the response.")
    thinking_tokens: int = Field(default=0, description="Reasoning tokens (if available).")
    latency_ms: int = Field(default=0, description="Request latency in milliseconds.")
    model_name: str = Field(default="unknown", description="The underlying model used.")
