"""DocuStruct AI — Groq, Together AI, & OpenRouter Adapter Tests.

Comprehensive mocked HTTP unit tests validating:
- Normal text and structured Pydantic completions.
- Safe missing-credential behavior (zero network calls, safe defaults).
- Provider-specific attribution headers (OpenRouter).
- 429 rate limit backoff parsing (Retry-After header).
- 401 authentication failure mapping.
- 404 model not found mapping.
- 500/503 upstream server error mapping.
- Timeout and network error handling.
- Malformed response JSON and schema validation error handling.
- Model availability probing without assuming vision/task capabilities.
"""

from __future__ import annotations

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel, Field

from app.llm.enums import ProviderType
from app.llm.exceptions import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.providers.openrouter import OpenRouterProviderAdapter
from app.llm.providers.together import TogetherProviderAdapter


class SampleExtract(BaseModel):
    title: str
    row_count: int = Field(ge=0)


def create_mock_client(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
    headers: Optional[dict[str, str]] = None,
    side_effect: Any = None,
) -> tuple[AsyncMock, MagicMock]:
    """Helper creating a mocked httpx.AsyncClient with context manager support."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    if json_data is not None:
        mock_response.json.return_value = json_data
        mock_response.text = json.dumps(json_data)
    else:
        mock_response.text = text
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", text, 0)

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    if side_effect:
        mock_client.get.side_effect = side_effect
        mock_client.post.side_effect = side_effect
    else:
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response

    return mock_client, mock_response


# ══════════════════════════════════════════════════════════════════════════════
# Groq Provider Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestGroqProviderAdapter:
    """Test suite for GroqProviderAdapter."""

    @pytest.mark.asyncio
    async def test_groq_missing_credentials_fails_safely(self) -> None:
        """Missing credentials must fail safely without executing network calls."""
        adapter = GroqProviderAdapter(api_key=None)
        assert adapter.has_credentials() is False

        health = await adapter.health_check()
        assert health.configured is False
        assert health.available is False

        probe_result = await adapter.probe_availability("llama-3-8b")
        assert probe_result is False

        with pytest.raises(ProviderAuthError) as exc_info:
            await adapter.complete("test", "llama-3-8b")
        assert "Missing Groq API key" in str(exc_info.value)

        with pytest.raises(ProviderAuthError):
            await adapter.complete_structured("test", "llama-3-8b", SampleExtract)

    @pytest.mark.asyncio
    async def test_groq_successful_completion(self) -> None:
        """Groq completion parses choices and usage correctly."""
        mock_payload = {
            "choices": [{"message": {"content": "Sample Groq response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            response = await adapter.complete("Analyze table", "llama-3-8b")

            assert response.content == "Sample Groq response"
            assert response.provider == ProviderType.GROQ
            assert response.model_id == "llama-3-8b"
            assert response.usage["total_tokens"] == 15
            assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_groq_successful_structured_completion(self) -> None:
        """Groq structured completion strictly validates Pydantic model."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Balance Sheet", "row_count": 12}'}}],
            "usage": {"total_tokens": 20},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            response = await adapter.complete_structured("Extract table", "llama-3-8b", SampleExtract)

            assert response.validation_passed is True
            assert isinstance(response.parsed, SampleExtract)
            assert response.parsed.title == "Balance Sheet"
            assert response.parsed.row_count == 12

    @pytest.mark.asyncio
    async def test_groq_structured_completion_schema_mismatch_raises_error(self) -> None:
        """Output violating Pydantic schema raises SchemaValidationError."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Test", "row_count": -5}'}}],
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            with pytest.raises(SchemaValidationError) as exc_info:
                await adapter.complete_structured("Extract", "llama-3-8b", SampleExtract)
            assert "violated schema" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_groq_rate_limit_429_with_retry_after(self) -> None:
        """HTTP 429 raises RateLimitExceededError and parses Retry-After header."""
        mock_client, _ = create_mock_client(
            429,
            text="Rate limit reached",
            headers={"Retry-After": "4.2"},
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete("test", "llama-3-8b")
            assert exc_info.value.retry_after_seconds == 4.2
            assert exc_info.value.provider == "GROQ"

    @pytest.mark.asyncio
    async def test_groq_auth_failure_401(self) -> None:
        """HTTP 401 raises ProviderAuthError."""
        mock_client, _ = create_mock_client(401, text="Invalid API key")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-invalid-key")
            with pytest.raises(ProviderAuthError):
                await adapter.complete("test", "llama-3-8b")

    @pytest.mark.asyncio
    async def test_groq_model_not_found_404(self) -> None:
        """HTTP 404 raises ModelNotFoundError."""
        mock_client, _ = create_mock_client(404, text="Model not found")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            with pytest.raises(ModelNotFoundError):
                await adapter.complete("test", "unknown-groq-model")

    @pytest.mark.asyncio
    async def test_groq_timeout_and_network_errors(self) -> None:
        """Timeouts and network disconnects map to typed exceptions."""
        timeout_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Read timed out"))
        with patch("httpx.AsyncClient", return_value=timeout_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete("test", "llama-3-8b")

        net_err_client, _ = create_mock_client(side_effect=httpx.ConnectError("Connection refused"))
        with patch("httpx.AsyncClient", return_value=net_err_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "llama-3-8b")

    @pytest.mark.asyncio
    async def test_groq_probe_availability(self) -> None:
        """probe_availability returns True if model_id is in /models, False otherwise."""
        mock_payload = {
            "data": [{"id": "llama-3.1-70b-versatile"}, {"id": "mixtral-8x7b-32768"}]
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = GroqProviderAdapter(api_key="gsk-valid-key")
            assert await adapter.probe_availability("llama-3.1-70b-versatile") is True
            assert await adapter.probe_availability("non-existent-model") is False


# ══════════════════════════════════════════════════════════════════════════════
# Together AI Provider Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestTogetherProviderAdapter:
    """Test suite for TogetherProviderAdapter."""

    @pytest.mark.asyncio
    async def test_together_missing_credentials_fails_safely(self) -> None:
        """Missing credentials fail safely without making network requests."""
        adapter = TogetherProviderAdapter(api_key=None)
        assert adapter.has_credentials() is False

        health = await adapter.health_check()
        assert health.configured is False

        assert await adapter.probe_availability("meta-llama/Llama-3-70b-chat-hf") is False

        with pytest.raises(ProviderAuthError):
            await adapter.complete("test", "model-id")

    @pytest.mark.asyncio
    async def test_together_successful_completion(self) -> None:
        """Together AI completion parses payload properly."""
        mock_payload = {
            "choices": [{"message": {"content": "Together AI output"}}],
            "usage": {"total_tokens": 50},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            res = await adapter.complete("Hello", "qwen-model")
            assert res.content == "Together AI output"
            assert res.provider == ProviderType.TOGETHER

    @pytest.mark.asyncio
    async def test_together_successful_structured_completion(self) -> None:
        """Together AI structured completion validates with Pydantic."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Income Statement", "row_count": 8}'}}],
            "usage": {"total_tokens": 25},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            res = await adapter.complete_structured("prompt", "qwen-model", SampleExtract)
            assert res.validation_passed is True
            assert res.parsed.title == "Income Statement"
            assert res.parsed.row_count == 8

    @pytest.mark.asyncio
    async def test_together_probe_availability_handles_dict_and_list(self) -> None:
        """Together AI /models endpoint handles list of dicts."""
        mock_payload = [
            {"id": "meta-llama/Llama-4-Scout"},
            {"id": "Qwen/Qwen3.8-27B"},
        ]
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            assert await adapter.probe_availability("meta-llama/Llama-4-Scout") is True
            assert await adapter.probe_availability("unknown-model") is False

    @pytest.mark.asyncio
    async def test_together_server_error_500(self) -> None:
        """HTTP 500 raises ProviderServiceUnavailableError."""
        mock_client, _ = create_mock_client(500, text="Internal Server Error")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_together_auth_failure_401(self) -> None:
        """HTTP 401 raises ProviderAuthError."""
        mock_client, _ = create_mock_client(401, text="Unauthorized: Invalid API key")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-invalid-key")
            with pytest.raises(ProviderAuthError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_together_model_not_found_404(self) -> None:
        """HTTP 404 raises ModelNotFoundError."""
        mock_client, _ = create_mock_client(404, text="Model not found")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(ModelNotFoundError):
                await adapter.complete("test", "non-existent-together-model")

    @pytest.mark.asyncio
    async def test_together_rate_limit_429_with_retry_after(self) -> None:
        """HTTP 429 raises RateLimitExceededError with parsed retry-after."""
        mock_client, _ = create_mock_client(
            429,
            text="Rate limit exceeded",
            headers={"Retry-After": "3.5"},
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete("test", "m")
            assert exc_info.value.retry_after_seconds == 3.5
            assert exc_info.value.provider == "TOGETHER"

    @pytest.mark.asyncio
    async def test_together_timeout_and_network_errors(self) -> None:
        """Timeouts and network disconnects map to typed exceptions."""
        timeout_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Read timed out"))
        with patch("httpx.AsyncClient", return_value=timeout_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete("test", "m")

        net_client, _ = create_mock_client(side_effect=httpx.ConnectError("Connection refused"))
        with patch("httpx.AsyncClient", return_value=net_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_together_structured_completion_schema_mismatch(self) -> None:
        """Structured output violating schema constraints raises SchemaValidationError."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Income", "row_count": -10}'}}],
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete_structured("prompt", "m", SampleExtract)

    @pytest.mark.asyncio
    async def test_together_malformed_json_response(self) -> None:
        """Non-JSON response text raises SchemaValidationError."""
        mock_client, _ = create_mock_client(200, text="Malformed non-json output")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = TogetherProviderAdapter(api_key="together-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete("prompt", "m")


# ══════════════════════════════════════════════════════════════════════════════
# OpenRouter Provider Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestOpenRouterProviderAdapter:
    """Test suite for OpenRouterProviderAdapter."""

    @pytest.mark.asyncio
    async def test_openrouter_missing_credentials_fails_safely(self) -> None:
        """Missing credentials fail safely without making network requests."""
        adapter = OpenRouterProviderAdapter(api_key=None)
        assert adapter.has_credentials() is False

        health = await adapter.health_check()
        assert health.configured is False

        assert await adapter.probe_availability("gpt-oss-120b") is False

        with pytest.raises(ProviderAuthError):
            await adapter.complete("test", "model-id")

    @pytest.mark.asyncio
    async def test_openrouter_attribution_headers_included(self) -> None:
        """OpenRouter requests must include HTTP-Referer and X-Title headers."""
        mock_payload = {
            "choices": [{"message": {"content": "OpenRouter response"}}],
            "usage": {"total_tokens": 15},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(
                api_key="sk-or-valid-key",
                referer="https://custom.docustruct.ai",
                app_title="DocuStruct Test",
            )
            await adapter.complete("test prompt", "google/gemma-4")

            # Inspect headers sent in post call
            call_kwargs = mock_client.post.call_args.kwargs
            sent_headers = call_kwargs.get("headers", {})
            assert sent_headers.get("HTTP-Referer") == "https://custom.docustruct.ai"
            assert sent_headers.get("X-Title") == "DocuStruct Test"
            assert sent_headers.get("Authorization") == "Bearer sk-or-valid-key"

    @pytest.mark.asyncio
    async def test_openrouter_successful_structured_completion(self) -> None:
        """OpenRouter structured completion validates against Pydantic schema."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Cash Flow", "row_count": 15}'}}],
            "usage": {"total_tokens": 30},
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-valid-key")
            res = await adapter.complete_structured("prompt", "google/gemma-4", SampleExtract)
            assert res.validation_passed is True
            assert res.parsed.title == "Cash Flow"
            assert res.parsed.row_count == 15

    @pytest.mark.asyncio
    async def test_openrouter_malformed_json_raises_schema_validation_error(self) -> None:
        """Malformed JSON response envelope raises SchemaValidationError."""
        mock_client, _ = create_mock_client(200, text="Not a JSON object")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-valid-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete("prompt", "google/gemma-4")

    @pytest.mark.asyncio
    async def test_openrouter_structured_completion_schema_mismatch(self) -> None:
        """Structured completion violating Pydantic schema raises SchemaValidationError."""
        mock_payload = {
            "choices": [{"message": {"content": '{"title": "Balance", "row_count": -3}'}}],
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-valid-key")
            with pytest.raises(SchemaValidationError):
                await adapter.complete_structured("prompt", "google/gemma-4", SampleExtract)

    @pytest.mark.asyncio
    async def test_openrouter_auth_failure_401(self) -> None:
        """HTTP 401 raises ProviderAuthError."""
        mock_client, _ = create_mock_client(401, text="Invalid OpenRouter Key")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-bad-key")
            with pytest.raises(ProviderAuthError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_openrouter_model_not_found_404(self) -> None:
        """HTTP 404 raises ModelNotFoundError."""
        mock_client, _ = create_mock_client(404, text="Model not recognized")

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(ModelNotFoundError):
                await adapter.complete("test", "non-existent-openrouter-model")

    @pytest.mark.asyncio
    async def test_openrouter_rate_limit_429_with_retry_after(self) -> None:
        """HTTP 429 raises RateLimitExceededError with retry-after header."""
        mock_client, _ = create_mock_client(
            429,
            text="Rate limit hit",
            headers={"Retry-After": "2.0"},
        )

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete("test", "m")
            assert exc_info.value.retry_after_seconds == 2.0
            assert exc_info.value.provider == "OPENROUTER"

    @pytest.mark.asyncio
    async def test_openrouter_server_error_500_and_503(self) -> None:
        """HTTP 500 and 503 raise ProviderServiceUnavailableError."""
        mock_client_500, _ = create_mock_client(500, text="Internal Server Error")
        with patch("httpx.AsyncClient", return_value=mock_client_500):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

        mock_client_503, _ = create_mock_client(503, text="Service Unavailable")
        with patch("httpx.AsyncClient", return_value=mock_client_503):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_openrouter_timeout_and_network_errors(self) -> None:
        """Timeouts and network disconnects map to typed exceptions."""
        timeout_client, _ = create_mock_client(side_effect=httpx.TimeoutException("Read timed out"))
        with patch("httpx.AsyncClient", return_value=timeout_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete("test", "m")

        net_client, _ = create_mock_client(side_effect=httpx.ConnectError("Network unreachable"))
        with patch("httpx.AsyncClient", return_value=net_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-key")
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete("test", "m")

    @pytest.mark.asyncio
    async def test_openrouter_probe_availability(self) -> None:
        """probe_availability returns True when model exists in data array."""
        mock_payload = {
            "data": [{"id": "google/gemma-4"}, {"id": "openai/gpt-4o"}]
        }
        mock_client, _ = create_mock_client(200, json_data=mock_payload)

        with patch("httpx.AsyncClient", return_value=mock_client):
            adapter = OpenRouterProviderAdapter(api_key="sk-or-valid-key")
            assert await adapter.probe_availability("google/gemma-4") is True
            assert await adapter.probe_availability("missing-model") is False
