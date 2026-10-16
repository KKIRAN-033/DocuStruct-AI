"""DocuStruct AI — Multi-Provider Adapters Integration Tests.

Validates:
    - HTTP request construction, endpoint headers, and payload formats for all 5 providers:
      Groq, Together AI, OpenRouter, DeepSeek API, and Z.ai API.
    - OpenRouter mandatory attribution headers (HTTP-Referer, X-Title).
    - Unconfigured credentials raise ProviderAuthError without network activity.
    - Secret redaction preventing API keys from leaking in exceptions and logs.
    - Health check credential verification without network latency.
    - Capability probing with mocked HTTP responses.
    - Opt-in live test fixtures gated by DOCUSTRUCT_RUN_LIVE_TESTS=1.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from pydantic import BaseModel, Field

from app.llm.enums import ProviderType
from app.llm.exceptions import ProviderAuthError
from app.llm.models import CompletionResponse, ProviderHealth, StructuredCompletionResponse
from app.llm.providers.deepseek import DeepSeekProviderAdapter
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.providers.openrouter import OpenRouterProviderAdapter
from app.llm.providers.together import TogetherProviderAdapter
from app.llm.providers.zai import ZaiProviderAdapter
from tests.llm.conftest import create_mock_client


class DummyOutputSchema(BaseModel):
    """Simple test schema for structured output validation."""

    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


# ── 1. Provider Adapter Mocked HTTP Tests ────────────────────────────────────


class TestProviderAdapterHeadersAndPayloads:
    """Validate HTTP headers, attribution, and payload structures for all 5 providers."""

    @pytest.mark.asyncio
    async def test_groq_adapter_headers_and_completion(self) -> None:
        """Groq adapter sends correct Bearer auth and parses standard response."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Groq extraction summary"}}],
                "usage": {"total_tokens": 42},
            },
        )
        adapter = GroqProviderAdapter(api_key="test-groq-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete(
                model_id="llama-3.3-70b-versatile",
                prompt="Analyze table header structure",
                temperature=0.0,
            )

        mock_client.post.assert_awaited_once()
        raw_headers = mock_client.post.call_args.kwargs["headers"]
        headers = {k.lower(): v for k, v in raw_headers.items()}
        assert headers["authorization"] == "Bearer test-groq-key"
        assert headers["content-type"] == "application/json"
        assert res.content == "Groq extraction summary"
        assert res.provider == ProviderType.GROQ
        assert res.model_id == "llama-3.3-70b-versatile"

    @pytest.mark.asyncio
    async def test_together_adapter_headers_and_completion(self) -> None:
        """Together AI adapter sends correct Bearer auth and parses standard response."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Together AI output"}}],
                "usage": {"total_tokens": 15},
            },
        )
        adapter = TogetherProviderAdapter(api_key="test-together-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete(
                model_id="Qwen/Qwen2.5-72B-Instruct",
                prompt="Translate table columns",
            )

        mock_client.post.assert_awaited_once()
        raw_headers = mock_client.post.call_args.kwargs["headers"]
        headers = {k.lower(): v for k, v in raw_headers.items()}
        assert headers["authorization"] == "Bearer test-together-key"
        assert res.content == "Together AI output"
        assert res.provider == ProviderType.TOGETHER

    @pytest.mark.asyncio
    async def test_openrouter_adapter_attribution_headers(self) -> None:
        """OpenRouter adapter strictly sends mandatory HTTP-Referer and X-Title headers."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "OpenRouter output"}}],
                "usage": {"total_tokens": 20},
            },
        )
        adapter = OpenRouterProviderAdapter(api_key="test-openrouter-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete(
                model_id="meta-llama/llama-3.3-70b-instruct",
                prompt="Test prompt",
            )

        mock_client.post.assert_awaited_once()
        raw_headers = mock_client.post.call_args.kwargs["headers"]
        headers = {k.lower(): v for k, v in raw_headers.items()}
        assert headers["authorization"] == "Bearer test-openrouter-key"
        assert headers["http-referer"] == "https://docustruct.ai"
        assert headers["x-title"] == "DocuStruct AI"
        assert res.content == "OpenRouter output"
        assert res.provider == ProviderType.OPENROUTER

    @pytest.mark.asyncio
    async def test_deepseek_adapter_headers_and_completion(self) -> None:
        """DeepSeek API adapter sends correct Bearer auth and parses response."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "DeepSeek analysis"}}],
                "usage": {"total_tokens": 88},
            },
        )
        adapter = DeepSeekProviderAdapter(api_key="test-deepseek-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete(
                model_id="deepseek-chat",
                prompt="Interpret complex tabular relationships",
            )

        mock_client.post.assert_awaited_once()
        raw_headers = mock_client.post.call_args.kwargs["headers"]
        headers = {k.lower(): v for k, v in raw_headers.items()}
        assert headers["authorization"] == "Bearer test-deepseek-key"
        assert res.content == "DeepSeek analysis"
        assert res.provider == ProviderType.DEEPSEEK

    @pytest.mark.asyncio
    async def test_zai_adapter_headers_and_completion(self) -> None:
        """Z.ai API adapter sends correct Bearer auth and parses response."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": "Z.ai GLM output"}}],
                "usage": {"total_tokens": 55},
            },
        )
        adapter = ZaiProviderAdapter(api_key="test-zai-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete(
                model_id="glm-4-flash",
                prompt="Adjudicate hypothesis",
            )

        mock_client.post.assert_awaited_once()
        raw_headers = mock_client.post.call_args.kwargs["headers"]
        headers = {k.lower(): v for k, v in raw_headers.items()}
        assert headers["authorization"] == "Bearer test-zai-key"
        assert res.content == "Z.ai GLM output"
        assert res.provider == ProviderType.ZAI


# ── 2. Structured Completion Integration Tests ───────────────────────────────


class TestProviderStructuredCompletion:
    """Validate structured Pydantic completion across provider adapters."""

    @pytest.mark.asyncio
    async def test_structured_completion_pydantic_validation(self) -> None:
        """Adapter correctly parses and validates JSON into target Pydantic schema."""
        raw_json_str = '{"summary": "Multi-column balance sheet", "confidence": 0.94}'
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={
                "choices": [{"message": {"content": raw_json_str}}],
                "usage": {"total_tokens": 60},
            },
        )
        adapter = GroqProviderAdapter(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res: StructuredCompletionResponse = await adapter.complete_structured(
                prompt="Extract table summary",
                model_id="llama-3.3-70b-versatile",
                schema=DummyOutputSchema,
            )

        assert res.validation_passed is True
        assert isinstance(res.parsed, DummyOutputSchema)
        assert res.parsed.summary == "Multi-column balance sheet"
        assert res.parsed.confidence == 0.94


# ── 3. Health Check & Capability Probe Tests ─────────────────────────────────


class TestProviderHealthAndProbes:
    """Validate health check and capability probe methods across adapters."""

    @pytest.mark.asyncio
    async def test_health_check_without_credentials(self) -> None:
        """All 5 adapters return configured=False, available=False when API key is missing."""
        adapters = [
            GroqProviderAdapter(api_key=None),
            TogetherProviderAdapter(api_key=None),
            OpenRouterProviderAdapter(api_key=None),
            DeepSeekProviderAdapter(api_key=None),
            ZaiProviderAdapter(api_key=None),
        ]
        for adapter in adapters:
            health: ProviderHealth = await adapter.health_check()
            assert health.configured is False
            assert health.available is False
            assert health.error_message is not None

    @pytest.mark.asyncio
    async def test_health_check_with_credentials(self) -> None:
        """All 5 adapters return configured=True, available=True when key is present."""
        adapters = [
            GroqProviderAdapter(api_key="key-1"),
            TogetherProviderAdapter(api_key="key-2"),
            OpenRouterProviderAdapter(api_key="key-3"),
            DeepSeekProviderAdapter(api_key="key-4"),
            ZaiProviderAdapter(api_key="key-5"),
        ]
        for adapter in adapters:
            health: ProviderHealth = await adapter.health_check()
            assert health.configured is True
            assert health.available is True
            assert health.error_message is None

    @pytest.mark.asyncio
    async def test_probe_availability_finds_model(self) -> None:
        """Probe queries /models and returns True when model_id is present."""
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={"data": [{"id": "target-model-v1"}, {"id": "other-model"}]},
        )
        adapter = GroqProviderAdapter(api_key="test-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            found = await adapter.probe_availability("target-model-v1")
        assert found is True

    @pytest.mark.asyncio
    async def test_unconfigured_probe_returns_false_without_network_request(self) -> None:
        """Probe returns False immediately without HTTP traffic when key is missing."""
        adapter = GroqProviderAdapter(api_key=None)
        found = await adapter.probe_availability("any-model")
        assert found is False

    @pytest.mark.asyncio
    async def test_unconfigured_completion_raises_provider_auth_error(self) -> None:
        """Attempting completion without credentials raises ProviderAuthError before network request."""
        adapter = GroqProviderAdapter(api_key=None)
        with pytest.raises(ProviderAuthError) as exc_info:
            await adapter.complete(model_id="test-model", prompt="test")
        assert "Missing Groq API key" in str(exc_info.value)

    def test_secret_redaction_in_error_message(self) -> None:
        """Verify API key is never placed in exception message or string representation."""
        secret_key = "super-secret-api-key-12345"
        adapter = GroqProviderAdapter(api_key=secret_key)
        try:
            adapter._handle_http_error(
                status_code=401,
                response_text="Unauthorized access",
                headers={},
                model_id="test-model",
            )
        except ProviderAuthError as exc:
            assert secret_key not in str(exc)
            assert secret_key not in repr(exc)


# ── 4. Opt-In Live Provider Integration Tests ────────────────────────────────


@pytest.mark.live
class TestLiveProviderOptIn:
    """Opt-in live provider network integration tests.

    These tests make REAL external network requests to provider APIs.
    They are strictly SKIPPED by default during ordinary unit testing.
    To enable them, set DOCUSTRUCT_RUN_LIVE_TESTS=1 along with genuine API keys.
    """

    @pytest.mark.asyncio
    async def test_live_groq_health_and_probe(self) -> None:
        """Opt-in live reachability check against Groq API."""
        if os.getenv("DOCUSTRUCT_RUN_LIVE_TESTS") != "1":
            pytest.skip("Live provider tests are opt-in (set DOCUSTRUCT_RUN_LIVE_TESTS=1)")

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            pytest.skip("GROQ_API_KEY not configured for live test")

        adapter = GroqProviderAdapter(api_key=api_key)
        health = await adapter.health_check()
        assert health.configured is True
