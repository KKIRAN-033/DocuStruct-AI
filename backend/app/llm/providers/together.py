"""DocuStruct AI — Together AI Provider Adapter.

Provider-neutral adapter for Together AI using standard asynchronous httpx.
Handles authentication, model availability probing, text/structured completions,
and HTTP status code error mapping.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional, TypeVar

import httpx
from pydantic import BaseModel

from app.llm.enums import ProviderType
from app.llm.exceptions import (
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    SchemaValidationError,
)
from app.llm.models import (
    CompletionResponse,
    ProviderHealth,
    StructuredCompletionResponse,
)
from app.llm.providers.base import BaseProviderAdapter

T = TypeVar("T", bound=BaseModel)


class TogetherProviderAdapter(BaseProviderAdapter):
    """Adapter for Together AI open-weight models and multimodal inference."""

    provider_type = ProviderType.TOGETHER

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://api.together.xyz/v1",
            timeout_seconds=timeout_seconds,
        )

    def _get_headers(self) -> dict[str, str]:
        """Return provider-specific HTTP headers."""
        if not self.has_credentials():
            raise ProviderAuthError(
                "Missing Together AI API key",
                provider=self.provider_type.value,
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def probe_availability(self, model_id: str) -> bool:
        """Probe Together AI endpoint to check if model_id exists in /models.

        Does NOT make network calls if credentials are missing.
        Does NOT treat model listing as proof of vision or task capability.
        """
        if not self.has_credentials():
            return False

        url = f"{self.base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    data = response.json()
                    # Together AI models list can be an array of objects or dict with 'data'
                    model_objs = data.get("data", data) if isinstance(data, dict) else data
                    if isinstance(model_objs, list):
                        model_ids = [m.get("id") for m in model_objs if isinstance(m, dict)]
                        return model_id in model_ids
                    return False
                if response.status_code == 404:
                    return False
                self._handle_http_error(
                    response.status_code,
                    response.text,
                    headers=dict(response.headers),
                    model_id=model_id,
                )
                return False
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Together AI probe timed out after {self.timeout_seconds}s: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderServiceUnavailableError(
                f"Together AI probe network request failed: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc

    async def complete(
        self,
        prompt: str,
        model_id: str,
        temperature: float = 0.0,
    ) -> CompletionResponse:
        """Execute text completion via Together AI chat completions endpoint."""
        if not self.has_credentials():
            raise ProviderAuthError(
                "Missing Together AI API key. Network request blocked.",
                provider=self.provider_type.value,
                model_id=model_id,
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=self._get_headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Together AI request timed out after {self.timeout_seconds}s: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderServiceUnavailableError(
                f"Together AI network request failed: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if response.status_code != 200:
            self._handle_http_error(
                response.status_code,
                response.text,
                headers=dict(response.headers),
                model_id=model_id,
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise SchemaValidationError(
                f"Failed to parse Together AI response envelope: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
                raw_output=response.text,
            ) from exc

        return CompletionResponse(
            content=content,
            raw_payload=data,
            usage=usage,
            latency_ms=latency_ms,
            provider=self.provider_type,
            model_id=model_id,
        )

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
        """Execute structured JSON completion via Together AI and validate with Pydantic."""
        if images:
            raise NotImplementedError(
                f"Multimodal image inputs are not supported by {self.provider_type.value} adapter."
            )
        if not self.has_credentials():
            raise ProviderAuthError(
                "Missing Together AI API key. Network request blocked.",
                provider=self.provider_type.value,
                model_id=model_id,
            )

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        sys_content = (
            system_prompt.strip()
            if system_prompt and system_prompt.strip()
            else "You are a structured data extractor. Return JSON conforming to the requested schema."
        )
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": sys_content,
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=self._get_headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                f"Together AI request timed out after {self.timeout_seconds}s: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderServiceUnavailableError(
                f"Together AI network request failed: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
            ) from exc

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if response.status_code != 200:
            self._handle_http_error(
                response.status_code,
                response.text,
                headers=dict(response.headers),
                model_id=model_id,
            )

        try:
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise SchemaValidationError(
                f"Failed to parse Together AI response envelope: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
                raw_output=response.text,
            ) from exc

        try:
            parsed_json = self._parse_json_payload(raw_content)
            validated = schema.model_validate(parsed_json)
        except Exception as exc:
            raise SchemaValidationError(
                f"Together AI output violated schema {schema.__name__}: {exc}",
                provider=self.provider_type.value,
                model_id=model_id,
                raw_output=raw_content,
            ) from exc

        return StructuredCompletionResponse(
            content=raw_content,
            raw_payload=data,
            usage=usage,
            latency_ms=latency_ms,
            provider=self.provider_type,
            model_id=model_id,
            parsed=validated,
            validation_passed=True,
        )

    async def health_check(self) -> ProviderHealth:
        """Verify credential presence without making network calls if unconfigured."""
        if not self.has_credentials():
            return ProviderHealth(
                provider=self.provider_type,
                available=False,
                configured=False,
                error_message="Missing TOGETHER_API_KEY",
            )
        return ProviderHealth(
            provider=self.provider_type,
            available=True,
            configured=True,
            error_message=None,
        )
