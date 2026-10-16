"""DocuStruct AI — Multi-LLM Typed Exception Hierarchy.

Maps provider-agnostic operational errors and HTTP failure states
into structured domain exceptions.
"""

from __future__ import annotations

from typing import Optional


class MultiLLMError(Exception):
    """Base exception for all Multi-LLM subsystem errors."""

    def __init__(self, message: str, provider: Optional[str] = None, model_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model_id = model_id


class ProviderAuthError(MultiLLMError):
    """Authentication or authorization failure (missing or invalid API key, HTTP 401/403)."""


class ModelNotFoundError(MultiLLMError):
    """Requested model identifier does not exist on the targeted provider (HTTP 404)."""


class RateLimitExceededError(MultiLLMError):
    """Provider rate limit or quota exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        retry_after_seconds: Optional[float] = None,
    ) -> None:
        super().__init__(message, provider=provider, model_id=model_id)
        self.retry_after_seconds = retry_after_seconds


class ProviderServiceUnavailableError(MultiLLMError):
    """Provider upstream 5xx error, server outage, or connection refusal."""


class ProviderTimeoutError(MultiLLMError):
    """Request exceeded configured timeout ceiling (connect or read timeout)."""


class SchemaValidationError(MultiLLMError):
    """Model completion failed strict Pydantic structured output validation."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        raw_output: Optional[str] = None,
    ) -> None:
        super().__init__(message, provider=provider, model_id=model_id)
        self.raw_output = raw_output
