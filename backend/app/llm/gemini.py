"""Real Gemini LLM Adapter implementation using google-genai."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

from pydantic import ValidationError
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.config import get_settings
from app.llm.adapter import LLMAdapter
from app.llm.exceptions import LLMValidationError, LLMProviderUnavailableError
from app.llm.schemas import LLMRequest, LLMResponse
from app.llm.limiter import GLOBAL_LIMITER, GLOBAL_METRICS


class GeminiLLMAdapter(LLMAdapter):
    """The real Google Gemini adapter."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
            
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_name = model_name or settings.gemini_model
        
        # Rate Limiting configuration
        self.max_rpm = settings.gemini_max_rpm
        self.max_retries = settings.gemini_max_retries
        self.initial_backoff = settings.gemini_initial_backoff_seconds

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Call the real Gemini API."""
        
        config_kwargs = {}
        if request.system_prompt:
            config_kwargs["system_instruction"] = request.system_prompt
            
        if request.response_schema:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = request.response_schema
            
        if request.max_output_tokens:
            config_kwargs["max_output_tokens"] = request.max_output_tokens
            
        config = types.GenerateContentConfig(**config_kwargs)

        import random
        import uuid
        
        start_time = time.time()
        req_id = request.request_id or str(uuid.uuid4())
        run_id = request.run_id or "unknown"
        node = request.node or "unknown"
        purpose = request.purpose or "unknown"
        
        logger.info(f"LLM_REQUEST_START: request_id={req_id} run_id={run_id} node={node} purpose={purpose} model={self.model_name}")
        
        # Enforce global rate limiter queue
        wait_seconds = GLOBAL_LIMITER.wait_if_needed(self.max_rpm)
        if wait_seconds > 0:
            GLOBAL_METRICS["gemini_wait_seconds"] += wait_seconds
            
        GLOBAL_METRICS["gemini_requests"] += 1
        
        attempt = 0
        final_status = "failed"
        
        for attempt_idx in range(self.max_retries):
            attempt = attempt_idx + 1
            attempt_start = time.time()
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=request.user_prompt,
                    config=config,
                )
                attempt_latency = int((time.time() - attempt_start) * 1000)
                logger.info(f"LLM_ATTEMPT: request_id={req_id} attempt={attempt} status=success latency={attempt_latency}ms")
                final_status = "success"
                break  # Success
            except APIError as e:
                attempt_latency = int((time.time() - attempt_start) * 1000)
                error_msg = str(e).lower()
                logger.warning(f"LLM_ATTEMPT: request_id={req_id} attempt={attempt} status=failed error_type=APIError latency={attempt_latency}ms reason='{error_msg}'")
                # Check if it's a quota/rate-limit issue
                if "quota" in error_msg or "429" in error_msg or "resource_exhausted" in error_msg:
                    GLOBAL_METRICS["gemini_rate_limited"] += 1
                    if attempt < self.max_retries:
                        GLOBAL_METRICS["gemini_retries"] += 1
                        # Exponential backoff with jitter
                        base = self.initial_backoff * (2 ** (attempt - 1))
                        jitter = random.uniform(0, 0.3 * base)
                        sleep_time = base + jitter
                        
                        logger.warning(f"Gemini Rate Limit hit. Retrying in {sleep_time:.2f}s... (Attempt {attempt+1}/{self.max_retries})")
                        time.sleep(sleep_time)
                        GLOBAL_METRICS["gemini_wait_seconds"] += sleep_time
                        continue
                raise LLMProviderUnavailableError(f"Gemini API Error: {e}") from e
            except Exception as e:
                attempt_latency = int((time.time() - attempt_start) * 1000)
                logger.warning(f"LLM_ATTEMPT: request_id={req_id} attempt={attempt} status=failed error_type=UnknownError latency={attempt_latency}ms reason='{str(e)}'")
                raise LLMProviderUnavailableError(f"Unexpected error communicating with Gemini: {e}") from e
        else:
            raise LLMProviderUnavailableError("Exceeded max retries for Gemini API due to rate limits.")

        raw_content = response.text or ""
        parsed_content: Any | None = None
        
        if request.response_schema:
            try:
                # google-genai returns valid JSON string when response_schema is used,
                # but we must parse it into the Pydantic model ourselves if the SDK didn't.
                # Actually `response.parsed` might be available if the SDK parses it, but 
                # we'll parse it manually to ensure it matches our exact Pydantic schema class.
                data = json.loads(raw_content)
                parsed_content = request.response_schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise LLMValidationError(f"Gemini output failed to parse: {e}") from e

        # Calculate tokens if provided by usage_metadata
        input_tokens = 0
        output_tokens = 0
        thinking_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0)
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"LLM_REQUEST_END: request_id={req_id} run_id={run_id} node={node} purpose={purpose} model={self.model_name} latency={latency_ms}ms status={final_status} attempt_count={attempt} input_tokens={input_tokens} output_tokens={output_tokens}")

        return LLMResponse(
            content=raw_content,
            parsed_content=parsed_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            thinking_tokens=thinking_tokens,
            latency_ms=latency_ms,
            model_name=self.model_name,
        )
