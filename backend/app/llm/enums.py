"""DocuStruct AI — Multi-LLM Domain Enumerations.

Typed string enumerations defining task types, modalities, providers,
and orthogonal multi-dimensional verification states.
"""

from __future__ import annotations

from enum import Enum


class TaskType(str, Enum):
    """Discrete task categories supported by the Multi-LLM architecture."""

    ROUTINE_CLASSIFICATION = "ROUTINE_CLASSIFICATION"
    COMPLEX_TABLE_INTERPRETATION = "COMPLEX_TABLE_INTERPRETATION"
    CONFLICTING_HYPOTHESES = "CONFLICTING_HYPOTHESES"
    CORRECTION_PROPOSAL = "CORRECTION_PROPOSAL"
    MULTILINGUAL_INTERPRETATION = "MULTILINGUAL_INTERPRETATION"
    VISUAL_TABLE_REVIEW = "VISUAL_TABLE_REVIEW"
    USER_EXPLANATION = "USER_EXPLANATION"


class Modality(str, Enum):
    """Input and processing modalities supported by candidate models."""

    TEXT = "TEXT"
    VISION = "VISION"


class ProviderType(str, Enum):
    """External LLM providers integrated via provider-neutral adapters."""

    GROQ = "GROQ"
    TOGETHER = "TOGETHER"
    OPENROUTER = "OPENROUTER"
    DEEPSEEK = "DEEPSEEK"
    ZAI = "ZAI"


class ModelExistenceStatus(str, Enum):
    """Verification state of a model's physical existence on a provider endpoint."""

    UNVERIFIED = "UNVERIFIED"
    CONFIRMED = "CONFIRMED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderAvailabilityStatus(str, Enum):
    """Operational availability status of a provider endpoint."""

    UNVERIFIED = "UNVERIFIED"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


class ConfigurationCredentialStatus(str, Enum):
    """Credential and configuration presence status for a provider/model."""

    MISSING_CREDENTIALS = "MISSING_CREDENTIALS"
    CONFIGURED = "CONFIGURED"


class IntegrationTestStatus(str, Enum):
    """Outcome of automated integration test probes against the candidate."""

    UNTESTED = "UNTESTED"
    PASSED = "PASSED"
    FAILED = "FAILED"
