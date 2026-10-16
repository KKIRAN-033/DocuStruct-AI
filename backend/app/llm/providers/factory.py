"""DocuStruct AI — Provider Factory.

Centralized factory for instantiating and caching configured provider adapters.
Decouples client modules from concrete provider classes and manages environment settings.
"""

from __future__ import annotations

from typing import Optional

from app.llm.config import MultiLLMSettings
from app.llm.enums import ProviderType
from app.llm.exceptions import MultiLLMError
from app.llm.models import CandidateModel
from app.llm.providers.base import BaseProviderAdapter
from app.llm.providers.deepseek import DeepSeekProviderAdapter
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.providers.openrouter import OpenRouterProviderAdapter
from app.llm.providers.together import TogetherProviderAdapter
from app.llm.providers.zai import ZaiProviderAdapter


class ProviderFactory:
    """Factory creating and caching provider adapters configured from settings."""

    _adapter_cache: dict[tuple[ProviderType, Optional[str], str, float], BaseProviderAdapter] = {}

    @classmethod
    def get_adapter(
        cls,
        provider_type: ProviderType,
        settings: Optional[MultiLLMSettings] = None,
    ) -> BaseProviderAdapter:
        """Get or create an initialized adapter instance for the specified provider."""
        settings = settings or MultiLLMSettings()
        api_key = settings.get_provider_key(provider_type)
        base_url = settings.get_provider_base_url(provider_type)
        timeout = settings.default_timeout_seconds

        cache_key = (provider_type, api_key, base_url, timeout)
        if cache_key in cls._adapter_cache:
            return cls._adapter_cache[cache_key]

        adapter: BaseProviderAdapter
        if provider_type == ProviderType.GROQ:
            adapter = GroqProviderAdapter(
                api_key=api_key,
                base_url=base_url or None,
                timeout_seconds=timeout,
            )
        elif provider_type == ProviderType.TOGETHER:
            adapter = TogetherProviderAdapter(
                api_key=api_key,
                base_url=base_url or None,
                timeout_seconds=timeout,
            )
        elif provider_type == ProviderType.OPENROUTER:
            adapter = OpenRouterProviderAdapter(
                api_key=api_key,
                base_url=base_url or None,
                timeout_seconds=timeout,
            )
        elif provider_type == ProviderType.DEEPSEEK:
            adapter = DeepSeekProviderAdapter(
                api_key=api_key,
                base_url=base_url or None,
                timeout_seconds=timeout,
            )
        elif provider_type == ProviderType.ZAI:
            adapter = ZaiProviderAdapter(
                api_key=api_key,
                base_url=base_url or None,
                timeout_seconds=timeout,
            )
        else:
            raise MultiLLMError(
                f"Unsupported provider type: {provider_type}",
                provider=str(provider_type),
            )

        cls._adapter_cache[cache_key] = adapter
        return adapter

    @classmethod
    def get_adapter_for_model(
        cls,
        candidate: CandidateModel,
        settings: Optional[MultiLLMSettings] = None,
    ) -> BaseProviderAdapter:
        """Get the configured provider adapter for a specific candidate model."""
        return cls.get_adapter(candidate.provider, settings=settings)

    @classmethod
    def reset_cache(cls) -> None:
        """Clear all cached adapter instances. Intended for testing."""
        cls._adapter_cache.clear()
