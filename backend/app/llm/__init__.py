"""DocuStruct AI — Multi-LLM Architecture Package.

Provides a provider-agnostic, multi-model intelligence subsystem
with declarative model registry, typed schemas, and uniform provider interfaces.
"""

from app.llm.config import MultiLLMSettings
from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    Modality,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    ProviderType,
    TaskType,
)
from app.llm.exceptions import (
    ModelNotFoundError,
    MultiLLMError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.fallback import (
    BoundedFallbackEngine,
    FallbackAttemptRecord,
    FallbackResult,
)
from app.llm.models import (
    CandidateModel,
    CompletionResponse,
    IntegrationTestRecord,
    ModelVerificationStatus,
    ProviderHealth,
    StructuredCompletionResponse,
    TimeoutRetryPolicy,
)
from app.llm.probe import CapabilityProbeResult, CapabilityProbeService
from app.llm.providers.base import BaseProviderAdapter
from app.llm.providers.factory import ProviderFactory
from app.llm.registry import ModelRegistry
from app.llm.router import TaskRouter, evaluate_candidate_eligibility
from app.llm.schemas import (
    CorrectionProposal,
    DiscrepancyHypothesis,
    ModelsStatusResponse,
    PageClassificationEnrichment,
    TableInterpretationResult,
    UserExplanationPayload,
)
from app.llm.workers import (
    BaseWorker,
    CorrectionWorker,
    DiscrepancyWorker,
    ExplanationWorker,
)

__all__ = [
    "BaseProviderAdapter",
    "BaseWorker",
    "BoundedFallbackEngine",
    "CandidateModel",
    "CapabilityProbeResult",
    "CapabilityProbeService",
    "CompletionResponse",
    "ConfigurationCredentialStatus",
    "CorrectionProposal",
    "CorrectionWorker",
    "DiscrepancyHypothesis",
    "DiscrepancyWorker",
    "ExplanationWorker",
    "FallbackAttemptRecord",
    "FallbackResult",
    "IntegrationTestRecord",
    "IntegrationTestStatus",
    "Modality",
    "ModelExistenceStatus",
    "ModelNotFoundError",
    "ModelRegistry",
    "ModelVerificationStatus",
    "ModelsStatusResponse",
    "MultiLLMError",
    "MultiLLMSettings",
    "PageClassificationEnrichment",
    "ProviderAuthError",
    "ProviderAvailabilityStatus",
    "ProviderFactory",
    "ProviderHealth",
    "ProviderServiceUnavailableError",
    "ProviderTimeoutError",
    "ProviderType",
    "RateLimitExceededError",
    "SchemaValidationError",
    "StructuredCompletionResponse",
    "TableInterpretationResult",
    "TaskRouter",
    "TaskType",
    "TimeoutRetryPolicy",
    "UserExplanationPayload",
    "evaluate_candidate_eligibility",
]
