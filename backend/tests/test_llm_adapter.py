"""Tests for the LLM Adapter and Mock Implementation."""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.llm.adapter import LLMAdapter
from app.llm.exceptions import LLMValidationError
from app.llm.mock import MockLLMAdapter
from app.llm.schemas import LLMRequest, LLMResponse


class MockFindingSchema(BaseModel):
    """A dummy schema to test structured output parsing."""
    title: str
    summary: str
    severity: str
    confidence: float


class MockExtractionSchema(BaseModel):
    findings: list[MockFindingSchema]


def test_mock_adapter_is_instance_of_protocol():
    """Verify the mock satisfies the structural LLMAdapter protocol."""
    adapter = MockLLMAdapter()
    assert isinstance(adapter, LLMAdapter)


def test_mock_adapter_basic_text_generation():
    """Verify basic text generation without a schema."""
    adapter = MockLLMAdapter(default_response="Hello World")
    
    request = LLMRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say something."
    )
    
    response = adapter.generate(request)
    
    assert isinstance(response, LLMResponse)
    assert response.content == "Hello World"
    assert response.parsed_content is None
    assert response.model_name == "mock-llm"
    assert response.input_tokens > 0
    assert response.output_tokens > 0


def test_mock_adapter_deterministic_extraction():
    """Verify the mock uses keyword routing to return deterministic JSON."""
    adapter = MockLLMAdapter()
    
    request = LLMRequest(
        system_prompt="You are an extraction bot.",
        user_prompt="Please extract claims from this text."
    )
    
    response = adapter.generate(request)
    
    assert "Mock Claim" in response.content


def test_mock_adapter_structured_parsing():
    """Verify the mock parses its deterministic output into a Pydantic model."""
    adapter = MockLLMAdapter()
    
    request = LLMRequest(
        system_prompt="Extract claims.",
        user_prompt="Do it.",
        response_schema=MockExtractionSchema
    )
    
    response = adapter.generate(request)
    
    # It should have successfully hydrated the Pydantic model
    assert isinstance(response.parsed_content, MockExtractionSchema)
    assert len(response.parsed_content.findings) == 1
    
    finding = response.parsed_content.findings[0]
    assert finding.title == "Mock Claim"
    assert finding.severity == "low"
    assert finding.confidence == 0.99


def test_mock_adapter_validation_error():
    """Verify a bad schema or bad mock output raises a validation error."""
    adapter = MockLLMAdapter()
    
    class UnmatchableSchema(BaseModel):
        missing_required_field: str
        
    request = LLMRequest(
        system_prompt="Extract claims.",
        user_prompt="Do it.",
        response_schema=UnmatchableSchema
    )
    
    # The mock will return the standard extraction JSON, which lacks `missing_required_field`.
    # This should fail Pydantic validation.
    with pytest.raises(LLMValidationError) as exc_info:
        adapter.generate(request)
        
    assert "Mock output failed to parse" in str(exc_info.value)
