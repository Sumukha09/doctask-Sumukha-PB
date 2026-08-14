"""Protocol for LLM Adapters."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.llm.schemas import LLMRequest, LLMResponse


@runtime_checkable
class LLMAdapter(Protocol):
    """The canonical interface for all LLM providers in FlowDocs.
    
    Nodes and services must depend on this interface, never on a specific
    provider's SDK (e.g. OpenAI/Anthropic).
    """

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for the given request.
        
        Args:
            request: The LLM request encapsulating prompts and optional schemas.
            
        Returns:
            An LLMResponse containing the raw text, token usage, and optionally
            the parsed BaseModel instance.
            
        Raises:
            LLMProviderUnavailableError: If the provider cannot be reached.
            LLMValidationError: If the output cannot be parsed into the requested schema.
        """
        ...
