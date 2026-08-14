"""Exceptions for the LLM Adapter layer."""

class LLMAdapterError(Exception):
    """Base exception for all LLM adapter errors."""
    pass


class LLMProviderUnavailableError(LLMAdapterError):
    """Raised when the underlying provider is unreachable, times out, or rate limits."""
    pass


class LLMValidationError(LLMAdapterError):
    """Raised when the LLM output fails to parse into the requested schema."""
    pass
