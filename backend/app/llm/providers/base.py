"""DocuStruct AI — Abstract Provider Adapter.

Uniform provider-neutral abstract base interface defining completion,
structured completion, model availability probing, and typed error handling.
Decouples application logic from third-party vendor SDKs.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, TypeVar

from pydantic import BaseModel

from app.llm.enums import ProviderType
from app.llm.exceptions import (
    ModelNotFoundError,
    MultiLLMError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    RateLimitExceededError,
)
from app.llm.models import (
    CompletionResponse,
    ProviderHealth,
    StructuredCompletionResponse,
)

T = TypeVar("T", bound=BaseModel)


class BaseProviderAdapter(ABC):
    """Uniform abstract interface implemented by all LLM provider adapters."""

    provider_type: ProviderType

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url or ""
        self.timeout_seconds = timeout_seconds

    def has_credentials(self) -> bool:
        """Check if valid non-empty credentials are configured."""
        return bool(self.api_key and self.api_key.strip())

    @staticmethod
    def _parse_json_payload(raw_content: str) -> Any:
        """Parse JSON from model response, stripping markdown code fences if present."""
        text = raw_content.strip()
        if "```" in text:
            start_fence = text.find("```")
            end_fence = text.rfind("```")
            if start_fence != -1 and end_fence != -1 and end_fence > start_fence:
                fence_block = text[start_fence:end_fence + 3]
                lines = fence_block.splitlines()
                if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
                    text = "\n".join(lines[1:-1]).strip()
        return json.loads(text)

    @abstractmethod
    async def probe_availability(self, model_id: str) -> bool:
        """Probe provider endpoint to verify whether a model identifier exists.

        Must return True only if confirmed by provider; False if not found (404)
        or unconfigured.
        """

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model_id: str,
        temperature: float = 0.0,
    ) -> CompletionResponse:
        """Execute a text completion request against the provider."""

    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        model_id: str,
        schema: type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        images: Optional[list[bytes]] = None,
    ) -> StructuredCompletionResponse:
        """Execute a completion and strictly validate the JSON response against schema."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Verify provider credential status and endpoint reachability."""

    def _handle_http_error(
        self,
        status_code: int,
        response_text: str,
        headers: Optional[dict[str, str]] = None,
        model_id: Optional[str] = None,
    ) -> None:
        """Map HTTP error status codes into typed Multi-LLM domain exceptions."""
        headers = headers or {}
        provider_name = self.provider_type.value if hasattr(self, "provider_type") else "UNKNOWN"

        if status_code in (401, 403):
            raise ProviderAuthError(
                f"Authentication failed for {provider_name} (HTTP {status_code}): {response_text}",
                provider=provider_name,
                model_id=model_id,
            )

        if status_code == 404:
            raise ModelNotFoundError(
                f"Model '{model_id}' not found on {provider_name} (HTTP 404): {response_text}",
                provider=provider_name,
                model_id=model_id,
            )

        if status_code == 429:
            retry_after_str = headers.get("retry-after") or headers.get("Retry-After")
            retry_after = None
            if retry_after_str:
                try:
                    retry_after = float(retry_after_str)
                except (ValueError, TypeError):
                    retry_after = None
            raise RateLimitExceededError(
                f"Rate limit exceeded on {provider_name} (HTTP 429): {response_text}",
                provider=provider_name,
                model_id=model_id,
                retry_after_seconds=retry_after,
            )

        if status_code >= 500:
            raise ProviderServiceUnavailableError(
                f"Upstream service unavailable on {provider_name} (HTTP {status_code}): {response_text}",
                provider=provider_name,
                model_id=model_id,
            )

        raise MultiLLMError(
            f"Unexpected error from {provider_name} (HTTP {status_code}): {response_text}",
            provider=provider_name,
            model_id=model_id,
        )
