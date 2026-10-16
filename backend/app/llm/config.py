"""DocuStruct AI — Multi-LLM Configuration.

Typed configuration schema using pydantic-settings. Manages provider API keys,
base URLs, candidate model ID overrides, and global timeout/retry parameters.
Safely handles missing credentials without crashes or hardcoding secrets.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.enums import ProviderType


class MultiLLMSettings(BaseSettings):
    """Configuration settings for Multi-LLM providers and candidate models."""

    # ── Provider API Credentials (Optional, sourced from environment) ────────
    groq_api_key: Optional[str] = Field(default=None, description="Groq API Key")
    together_api_key: Optional[str] = Field(default=None, description="Together AI API Key")
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API Key")
    deepseek_api_key: Optional[str] = Field(default=None, description="DeepSeek API Key")
    zai_api_key: Optional[str] = Field(default=None, description="Z.ai API Key")

    # ── Provider Base URLs ───────────────────────────────────────────────────
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    together_base_url: str = Field(default="https://api.together.xyz/v1")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")
    zai_base_url: str = Field(default="https://api.z.ai/v1")

    # ── Candidate Model Exact ID Overrides ───────────────────────────────────
    docustruct_model_gpt_oss_20b_id: Optional[str] = Field(default=None)
    docustruct_model_gpt_oss_120b_id: Optional[str] = Field(default=None)
    docustruct_model_deepseek_v4_1_flash_id: Optional[str] = Field(default=None)
    docustruct_model_glm_5_3_flash_id: Optional[str] = Field(default=None)
    docustruct_model_qwen_3_8_27b_id: Optional[str] = Field(default=None)
    docustruct_model_llama_4_scout_id: Optional[str] = Field(default=None)
    docustruct_model_gemma_4_id: Optional[str] = Field(default=None)

    # ── Global Timeout and Retry Defaults ────────────────────────────────────
    default_timeout_seconds: float = Field(default=30.0, gt=0.0)
    default_max_retries: int = Field(default=2, ge=0)
    default_backoff_base_seconds: float = Field(default=1.5, ge=0.5)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def has_provider_credentials(self, provider: ProviderType) -> bool:
        """Check whether valid non-empty credentials are configured for a provider."""
        key = self.get_provider_key(provider)
        return bool(key and key.strip())

    def get_provider_key(self, provider: ProviderType) -> Optional[str]:
        """Retrieve the configured API key for a specified provider."""
        mapping = {
            ProviderType.GROQ: self.groq_api_key,
            ProviderType.TOGETHER: self.together_api_key,
            ProviderType.OPENROUTER: self.openrouter_api_key,
            ProviderType.DEEPSEEK: self.deepseek_api_key,
            ProviderType.ZAI: self.zai_api_key,
        }
        return mapping.get(provider)

    def get_provider_base_url(self, provider: ProviderType) -> str:
        """Retrieve the base URL for a specified provider."""
        mapping = {
            ProviderType.GROQ: self.groq_base_url,
            ProviderType.TOGETHER: self.together_base_url,
            ProviderType.OPENROUTER: self.openrouter_base_url,
            ProviderType.DEEPSEEK: self.deepseek_base_url,
            ProviderType.ZAI: self.zai_base_url,
        }
        return mapping.get(provider, "")

    def get_model_id_override(self, config_key: str) -> Optional[str]:
        """Look up environment model ID override by configuration key."""
        normalized_key = config_key.lower()
        return getattr(self, normalized_key, None)
