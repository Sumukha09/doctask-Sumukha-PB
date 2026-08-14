"""Tests for the real Gemini LLM Adapter."""
from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest
from pydantic import BaseModel
from google.genai.errors import APIError

from app.llm.adapter import LLMAdapter
from app.llm.exceptions import LLMValidationError, LLMProviderUnavailableError
from app.llm.schemas import LLMRequest
from app.llm.gemini import GeminiLLMAdapter


class DummySchema(BaseModel):
    message: str


def test_gemini_adapter_implements_protocol():
    """Verify GeminiLLMAdapter satisfies the structural LLMAdapter protocol."""
    # We mock the setting to allow instantiation without a real API key
    with patch("app.llm.gemini.get_settings") as mock_get_settings:
        mock_get_settings.return_value.gemini_api_key = "fake_key"
        mock_get_settings.return_value.gemini_max_rpm = 10
        mock_get_settings.return_value.gemini_max_retries = 1
        mock_get_settings.return_value.gemini_initial_backoff_seconds = 0.0
        with patch("app.llm.gemini.genai.Client"):
            adapter = GeminiLLMAdapter()
            assert isinstance(adapter, LLMAdapter)


def test_gemini_adapter_missing_key_raises_error():
    """Verify instantiation fails clearly if GEMINI_API_KEY is omitted."""
    with patch("app.llm.gemini.get_settings") as mock_get_settings:
        mock_get_settings.return_value.gemini_api_key = None
        
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY environment variable is not set"):
            GeminiLLMAdapter()


def test_gemini_adapter_wraps_api_errors():
    """Verify raw SDK errors are securely translated into our custom domain exception."""
    with patch("app.llm.gemini.get_settings") as mock_get_settings:
        mock_get_settings.return_value.gemini_api_key = "fake_key"
        mock_get_settings.return_value.gemini_max_rpm = 10
        mock_get_settings.return_value.gemini_max_retries = 1
        mock_get_settings.return_value.gemini_initial_backoff_seconds = 0.0
        
        with patch("app.llm.gemini.genai.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance
            
            # Simulate a Google API Error
            mock_client_instance.models.generate_content.side_effect = APIError(message="Rate limit exceeded", code=429)
            
            adapter = GeminiLLMAdapter()
            req = LLMRequest(system_prompt="sys", user_prompt="usr")
            
            with pytest.raises(LLMProviderUnavailableError, match="Gemini API Error"):
                adapter.generate(req)


def test_gemini_adapter_wraps_validation_errors():
    """Verify bad JSON from Gemini is wrapped into our custom domain exception."""
    with patch("app.llm.gemini.get_settings") as mock_get_settings:
        mock_get_settings.return_value.gemini_api_key = "fake_key"
        mock_get_settings.return_value.gemini_max_rpm = 10
        mock_get_settings.return_value.gemini_max_retries = 1
        mock_get_settings.return_value.gemini_initial_backoff_seconds = 0.0
        
        with patch("app.llm.gemini.genai.Client") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_client_class.return_value = mock_client_instance
            
            # Simulate a success response but with garbage JSON text
            mock_response = MagicMock()
            mock_response.text = "This is not valid JSON"
            mock_client_instance.models.generate_content.return_value = mock_response
            
            adapter = GeminiLLMAdapter()
            req = LLMRequest(
                system_prompt="sys", 
                user_prompt="usr",
                response_schema=DummySchema
            )
            
            with pytest.raises(LLMValidationError, match="Gemini output failed to parse"):
                adapter.generate(req)


@pytest.mark.skipif(
    not os.getenv("FLOWDOCS_REAL_LLM_TESTS") or not os.getenv("GEMINI_API_KEY"),
    reason="Live Gemini tests are opt-in only. Set FLOWDOCS_REAL_LLM_TESTS=1 and GEMINI_API_KEY."
)
def test_real_gemini_api_call():
    """OPT-IN: Make one minimal real request to Gemini and verify it conforms."""
    # Instantiating reads the real settings. Since we didn't mock it, it uses the live key.
    adapter = GeminiLLMAdapter()
    
    req = LLMRequest(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say exactly the words: 'hello world', then return it in JSON.",
        response_schema=DummySchema
    )
    
    response = adapter.generate(req)
    
    # 1. Check raw output
    assert response.content is not None
    assert response.model_name == "gemini-3.1-flash-lite"
    
    # 2. Check structured parsing worked natively
    assert response.parsed_content is not None
    assert isinstance(response.parsed_content, DummySchema)
    assert "hello world" in response.parsed_content.message.lower()
    
    # 3. Check token counts are somewhat realistic
    assert response.input_tokens > 0
    assert response.output_tokens > 0
