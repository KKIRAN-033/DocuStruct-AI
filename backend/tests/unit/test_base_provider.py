"""DocuStruct AI — BaseProviderAdapter & Error Taxonomy Unit Tests.

Validates:
    - BaseProviderAdapter interface methods and credential checks.
    - HTTP error code mapping into typed MultiLLM exceptions.
    - RateLimitExceededError parsing of Retry-After headers.
    - Structured output validation and SchemaValidationError enforcement.
"""

from __future__ import annotations

import json
from typing import Any, Optional, TypeVar

import pytest
from pydantic import BaseModel, Field

from app.llm.enums import ProviderType
from app.llm.exceptions import (
    ModelNotFoundError,
    MultiLLMError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.models import (
    CompletionResponse,
    ProviderHealth,
    StructuredCompletionResponse,
)
from app.llm.providers.base import BaseProviderAdapter

T = TypeVar("T", bound=BaseModel)


# ── Test Schemas ─────────────────────────────────────────────────────────────


class SampleClassification(BaseModel):
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class MockProviderAdapter(BaseProviderAdapter):
    """Concrete test implementation of BaseProviderAdapter."""

    provider_type = ProviderType.OPENROUTER

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_response_text: str = '{"category": "FINANCIAL", "confidence": 0.95}',
        mock_probe_result: bool = True,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url)
        self.mock_response_text = mock_response_text
        self.mock_probe_result = mock_probe_result

    async def probe_availability(self, model_id: str) -> bool:
        if not self.has_credentials():
            return False
        return self.mock_probe_result

    async def complete(
        self,
        prompt: str,
        model_id: str,
        temperature: float = 0.0,
    ) -> CompletionResponse:
        if not self.has_credentials():
            raise ProviderAuthError("Missing API key", provider="OPENROUTER", model_id=model_id)
        return CompletionResponse(
            content=self.mock_response_text,
            raw_payload={"id": "mock_id"},
            usage={"total_tokens": 42},
            latency_ms=12.5,
            provider=self.provider_type,
            model_id=model_id,
        )

    async def complete_structured(
        self,
        prompt: str,
        model_id: str,
        schema: type[T],
    ) -> StructuredCompletionResponse:
        raw = await self.complete(prompt, model_id)
        try:
            data = json.loads(raw.content)
            parsed = schema.model_validate(data)
            return StructuredCompletionResponse(
                content=raw.content,
                raw_payload=raw.raw_payload,
                usage=raw.usage,
                latency_ms=raw.latency_ms,
                provider=raw.provider,
                model_id=raw.model_id,
                parsed=parsed,
                validation_passed=True,
            )
        except Exception as exc:
            raise SchemaValidationError(
                f"Validation failed: {exc}",
                provider="OPENROUTER",
                model_id=model_id,
                raw_output=raw.content,
            ) from exc

    async def health_check(self) -> ProviderHealth:
        has_creds = self.has_credentials()
        return ProviderHealth(
            provider=self.provider_type,
            available=has_creds,
            configured=has_creds,
            error_message=None if has_creds else "Missing API key",
        )


# ── Test Suite ───────────────────────────────────────────────────────────────


class TestBaseProviderAdapterContracts:
    """Test BaseProviderAdapter base behaviors and credential validations."""

    def test_credential_detection(self) -> None:
        """has_credentials distinguishes between valid keys and None/empty."""
        adapter_none = MockProviderAdapter(api_key=None)
        assert adapter_none.has_credentials() is False

        adapter_empty = MockProviderAdapter(api_key="   ")
        assert adapter_empty.has_credentials() is False

        adapter_valid = MockProviderAdapter(api_key="sk-real-test-key")
        assert adapter_valid.has_credentials() is True

    @pytest.mark.asyncio
    async def test_health_check_reporting(self) -> None:
        """Health check reflects credential configuration."""
        unconfigured = MockProviderAdapter(api_key=None)
        health = await unconfigured.health_check()
        assert health.configured is False
        assert health.available is False

        configured = MockProviderAdapter(api_key="sk-test-key")
        health = await configured.health_check()
        assert health.configured is True
        assert health.available is True


class TestHTTPErrorMapping:
    """Test standard HTTP status code mapping into domain exceptions."""

    def test_auth_error_mapping(self) -> None:
        adapter = MockProviderAdapter(api_key="test")
        with pytest.raises(ProviderAuthError) as exc_info:
            adapter._handle_http_error(401, "Invalid API Key", model_id="gpt-oss")
        assert "Authentication failed" in str(exc_info.value)

        with pytest.raises(ProviderAuthError):
            adapter._handle_http_error(403, "Forbidden", model_id="gpt-oss")

    def test_model_not_found_mapping(self) -> None:
        adapter = MockProviderAdapter(api_key="test")
        with pytest.raises(ModelNotFoundError) as exc_info:
            adapter._handle_http_error(404, "Model not recognized", model_id="unknown-model")
        assert "Model 'unknown-model' not found" in str(exc_info.value)

    def test_rate_limit_mapping_with_retry_after(self) -> None:
        adapter = MockProviderAdapter(api_key="test")
        with pytest.raises(RateLimitExceededError) as exc_info:
            adapter._handle_http_error(
                429,
                "Too many requests",
                headers={"retry-after": "5.5"},
                model_id="fast-model",
            )
        assert exc_info.value.retry_after_seconds == 5.5

    def test_server_error_mapping(self) -> None:
        adapter = MockProviderAdapter(api_key="test")
        with pytest.raises(ProviderServiceUnavailableError):
            adapter._handle_http_error(500, "Internal Server Error", model_id="model-a")

        with pytest.raises(ProviderServiceUnavailableError):
            adapter._handle_http_error(503, "Service Overloaded", model_id="model-a")

    def test_generic_error_mapping(self) -> None:
        adapter = MockProviderAdapter(api_key="test")
        with pytest.raises(MultiLLMError):
            adapter._handle_http_error(400, "Bad Request", model_id="model-a")


class TestStructuredCompletionValidation:
    """Test Pydantic structured output validation and error enforcement."""

    @pytest.mark.asyncio
    async def test_valid_structured_completion(self) -> None:
        """Valid JSON parses into the target Pydantic schema."""
        adapter = MockProviderAdapter(
            api_key="sk-test",
            mock_response_text='{"category": "FINANCIAL", "confidence": 0.95}',
        )
        result = await adapter.complete_structured("prompt", "test-model", SampleClassification)
        assert result.validation_passed is True
        assert isinstance(result.parsed, SampleClassification)
        assert result.parsed.category == "FINANCIAL"
        assert result.parsed.confidence == 0.95

    @pytest.mark.asyncio
    async def test_invalid_schema_structured_completion_raises_error(self) -> None:
        """Invalid schema (missing field, wrong type, out of bounds) raises SchemaValidationError."""
        # confidence is out of bounds (> 1.0)
        adapter = MockProviderAdapter(
            api_key="sk-test",
            mock_response_text='{"category": "FINANCIAL", "confidence": 5.0}',
        )
        with pytest.raises(SchemaValidationError) as exc_info:
            await adapter.complete_structured("prompt", "test-model", SampleClassification)
        assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_json_raises_schema_validation_error(self) -> None:
        """Non-JSON text raises SchemaValidationError."""
        adapter = MockProviderAdapter(
            api_key="sk-test",
            mock_response_text='This is not JSON text',
        )
        with pytest.raises(SchemaValidationError):
            await adapter.complete_structured("prompt", "test-model", SampleClassification)
