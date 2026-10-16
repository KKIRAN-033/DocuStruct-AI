"""DocuStruct AI — Multi-LLM Domain Models & Envelopes.

Typed Pydantic v2 contracts for candidate models, multi-dimensional
verification status, completion envelopes, and provider health.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    Modality,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    ProviderType,
    TaskType,
)


class TimeoutRetryPolicy(BaseModel):
    """Timeout and retry backoff parameters for a candidate model."""

    timeout_seconds: float = Field(default=30.0, gt=0.0)
    max_retries: int = Field(default=2, ge=0)
    backoff_base_seconds: float = Field(default=1.5, ge=0.5)


class IntegrationTestRecord(BaseModel):
    """Timestamped audit record of the latest integration test probe."""

    status: IntegrationTestStatus
    timestamp: str
    latency_ms: Optional[float] = None
    error_code: Optional[str] = None


class ModelVerificationStatus(BaseModel):
    """Four-part orthogonal operational verification status.

    Decomposes model operational readiness into four independent dimensions
    to prevent false assumptions of capability based solely on configuration.
    """

    existence: ModelExistenceStatus = ModelExistenceStatus.UNVERIFIED
    provider_availability: ProviderAvailabilityStatus = ProviderAvailabilityStatus.UNVERIFIED
    credentials: ConfigurationCredentialStatus = ConfigurationCredentialStatus.MISSING_CREDENTIALS
    test_result: IntegrationTestStatus = IntegrationTestStatus.UNTESTED

    @property
    def is_operational(self) -> bool:
        """A model is operational only when confirmed, available, configured, and tested."""
        return (
            self.existence == ModelExistenceStatus.CONFIRMED
            and self.provider_availability == ProviderAvailabilityStatus.AVAILABLE
            and self.credentials == ConfigurationCredentialStatus.CONFIGURED
            and self.test_result == IntegrationTestStatus.PASSED
        )


class CandidateModel(BaseModel):
    """Declarative specification for an AI candidate model.

    Enforces explicit declaration of exact model IDs, provider mappings,
    supported modalities, task affinities, and multi-dimensional verification state.
    """

    model_config = ConfigDict(protected_namespaces=())

    candidate_name: str
    exact_model_id: str = "UNVERIFIED"
    provider: ProviderType
    supported_modalities: list[Modality] = Field(default_factory=lambda: [Modality.TEXT])
    supported_tasks: list[TaskType] = Field(default_factory=list)
    configuration_key: str
    enabled_state: bool = False
    verification_status: ModelVerificationStatus = Field(default_factory=ModelVerificationStatus)
    routing_priority: int = 1
    timeout_retry_policy: TimeoutRetryPolicy = Field(default_factory=TimeoutRetryPolicy)
    fallback_eligibility: bool = True
    last_integration_test_result: Optional[IntegrationTestRecord] = None


class CompletionResponse(BaseModel):
    """Standardized response envelope returned by provider adapters."""

    model_config = ConfigDict(protected_namespaces=())

    content: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    provider: ProviderType
    model_id: str


class StructuredCompletionResponse(BaseModel):
    """Structured response envelope containing validated Pydantic model output."""

    model_config = ConfigDict(protected_namespaces=())

    content: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    provider: ProviderType
    model_id: str
    parsed: Any
    validation_passed: bool = True


class ProviderHealth(BaseModel):
    """Operational health status of a provider adapter."""

    provider: ProviderType
    available: bool
    configured: bool
    error_message: Optional[str] = None
