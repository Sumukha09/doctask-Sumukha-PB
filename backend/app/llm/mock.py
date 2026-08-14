"""A deterministic, mock implementation of the LLMAdapter."""
from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.llm.adapter import LLMAdapter
from app.llm.exceptions import LLMValidationError
from app.llm.schemas import LLMRequest, LLMResponse


class MockLLMAdapter(LLMAdapter):
    """A deterministic mock LLM adapter for automated tests.
    
    This adapter makes zero network calls and requires no API keys.
    It returns deterministic outputs based on keyword matching in the prompt.
    """

    def __init__(self, default_response: str = "Mock response"):
        self.default_response = default_response

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Simulate LLM generation deterministically."""
        
        # 1. Determine the raw string response
        raw_content = self._route_mock_response(request)
        
        # 2. Handle structured output validation if requested
        parsed_content: Any | None = None
        if request.response_schema is not None:
            try:
                # Assuming the mock raw_content is valid JSON
                data = json.loads(raw_content)
                parsed_content = request.response_schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise LLMValidationError(f"Mock output failed to parse: {e}") from e
                
        # 3. Calculate fake tokens deterministically based on string length
        input_tokens = len(request.system_prompt.split()) + len(request.user_prompt.split())
        output_tokens = len(raw_content.split())
        
        return LLMResponse(
            content=raw_content,
            parsed_content=parsed_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_name="mock-llm",
        )
        
    def _route_mock_response(self, request: LLMRequest) -> str:
        """Return a deterministic string based on the prompt content."""
        prompt = (request.system_prompt + " " + request.user_prompt).lower()
        
        if "extract claims" in prompt:
            return json.dumps({
                "findings": [
                    {
                        "title": "Mock Claim",
                        "summary": "This is a deterministic mock extraction.",
                        "severity": "low",
                        "confidence": 0.99
                    }
                ]
            })
            
        if "analyze" in prompt or "verify" in prompt:
            return json.dumps({
                "is_supported": True,
                "reasoning": "Mock verification logic says yes."
            })
            
        if request.response_schema:
            # If a schema is requested but no keywords match, try to return an empty dict
            return "{}"

        return self.default_response
