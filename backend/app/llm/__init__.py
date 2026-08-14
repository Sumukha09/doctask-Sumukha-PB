"""LLM Adapter interface and implementations.

This package provides a unified abstraction over LLM providers, ensuring the
domain and workflow logic is decoupled from specific SDKs like OpenAI or Anthropic.
"""

from app.llm.adapter import LLMAdapter
from app.llm.mock import MockLLMAdapter
from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.exceptions import LLMAdapterError, LLMProviderUnavailableError, LLMValidationError

__all__ = [
    "LLMAdapter",
    "MockLLMAdapter",
    "LLMRequest",
    "LLMResponse",
    "LLMAdapterError",
    "LLMProviderUnavailableError",
    "LLMValidationError",
]
