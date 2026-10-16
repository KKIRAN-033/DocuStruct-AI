"""DocuStruct AI — Multi-LLM Model Registry Unit Tests.

Validates:
    - All seven named candidate models are registered with exact string names.
    - Explicit fields are defined on every candidate.
    - Initial verification status is strictly UNVERIFIED, MISSING_CREDENTIALS, and UNTESTED.
    - Enabled state defaults to False and is_operational returns False.
    - Vision modality remains unverified and unenabled without empirical evidence.
    - Priority-based task retrieval works as specified.
    - MultiLLMSettings loads safely without environment variables and syncs credential states.
"""

from __future__ import annotations

import pytest

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
from app.llm.models import CandidateModel
from app.llm.registry import ModelRegistry

EXPECTED_CANDIDATE_NAMES = [
    "GPT-OSS 20B",
    "GPT-OSS 120B",
    "DeepSeek V4.1 Flash",
    "GLM-5.3-Flash through Z.ai",
    "Qwen3.8-27B",
    "Llama 4 Scout",
    "Gemma 4",
]


class TestModelRegistryInitialization:
    """Test registration, exact candidate names, and initial verification status."""

    def test_all_seven_exact_named_candidates_registered(self) -> None:
        """Every specified candidate must be registered with its exact string name."""
        registry = ModelRegistry()
        candidates = registry.list_candidates()
        assert len(candidates) == 7

        registered_names = [c.candidate_name for c in candidates]
        assert registered_names == EXPECTED_CANDIDATE_NAMES

    def test_candidate_explicit_fields_presence(self) -> None:
        """Each candidate must have all 12 required metadata fields populated."""
        assert len(CandidateModel.model_fields) == 12
        expected_fields = {
            "candidate_name",
            "exact_model_id",
            "provider",
            "supported_modalities",
            "supported_tasks",
            "configuration_key",
            "enabled_state",
            "verification_status",
            "routing_priority",
            "timeout_retry_policy",
            "fallback_eligibility",
            "last_integration_test_result",
        }
        assert set(CandidateModel.model_fields.keys()) == expected_fields

        registry = ModelRegistry()
        for name in EXPECTED_CANDIDATE_NAMES:
            candidate = registry.get_candidate(name)
            assert candidate is not None, f"Candidate {name} missing from registry"
            assert candidate.candidate_name == name
            assert isinstance(candidate.exact_model_id, str)
            assert isinstance(candidate.provider, ProviderType)
            assert isinstance(candidate.supported_modalities, list)
            assert len(candidate.supported_modalities) >= 1
            assert isinstance(candidate.supported_tasks, list)
            assert len(candidate.supported_tasks) >= 1
            assert isinstance(candidate.configuration_key, str)
            assert isinstance(candidate.enabled_state, bool)
            assert isinstance(candidate.routing_priority, int)
            assert candidate.timeout_retry_policy.timeout_seconds > 0.0
            assert candidate.timeout_retry_policy.max_retries >= 0
            assert candidate.timeout_retry_policy.backoff_base_seconds >= 0.5
            assert isinstance(candidate.fallback_eligibility, bool)
            assert hasattr(candidate, "verification_status")
            assert hasattr(candidate, "last_integration_test_result")

    def test_strict_unverified_initial_status_preserved(self) -> None:
        """Initial verification status must remain strictly UNVERIFIED and UNTESTED."""
        registry = ModelRegistry()
        for candidate in registry.list_candidates():
            # Model existence must not be assumed without dynamic probe
            assert candidate.verification_status.existence == ModelExistenceStatus.UNVERIFIED
            assert candidate.verification_status.provider_availability == ProviderAvailabilityStatus.UNVERIFIED
            assert candidate.verification_status.credentials == ConfigurationCredentialStatus.MISSING_CREDENTIALS
            assert candidate.verification_status.test_result == IntegrationTestStatus.UNTESTED

            # Must not be enabled by default
            assert candidate.enabled_state is False

            # Model ID must remain UNVERIFIED
            assert candidate.exact_model_id == "UNVERIFIED"

            # is_operational must return False
            assert candidate.verification_status.is_operational is False

    def test_unverified_modalities_not_enabled(self) -> None:
        """Vision modality must not be enabled for next-gen models without evidence."""
        registry = ModelRegistry()
        for candidate in registry.list_candidates():
            # Modality list must contain only verified modalities (TEXT)
            assert candidate.supported_modalities == [Modality.TEXT], (
                f"{candidate.candidate_name} enabled unverified modalities: {candidate.supported_modalities}"
            )


class TestTaskAffinitiesAndRoutingPriority:
    """Test task affinity mappings and priority sorting."""

    def test_routine_classification_task_candidates(self) -> None:
        """Routine classification candidates ordered by priority."""
        registry = ModelRegistry()
        candidates = registry.get_candidates_for_task(TaskType.ROUTINE_CLASSIFICATION)
        names = [c.candidate_name for c in candidates]
        assert "GPT-OSS 20B" in names
        assert candidates[0].candidate_name == "GPT-OSS 20B"

    def test_complex_table_interpretation_task_candidates(self) -> None:
        """Complex table interpretation candidates."""
        registry = ModelRegistry()
        candidates = registry.get_candidates_for_task(TaskType.COMPLEX_TABLE_INTERPRETATION)
        names = [c.candidate_name for c in candidates]
        assert "DeepSeek V4.1 Flash" in names
        assert "GPT-OSS 120B" in names
        assert "GLM-5.3-Flash through Z.ai" in names

    def test_conflicting_hypotheses_task_candidates(self) -> None:
        """Conflicting hypotheses adjudication candidates."""
        registry = ModelRegistry()
        candidates = registry.get_candidates_for_task(TaskType.CONFLICTING_HYPOTHESES)
        names = [c.candidate_name for c in candidates]
        assert "GPT-OSS 120B" in names
        assert "GLM-5.3-Flash through Z.ai" in names

    def test_multilingual_interpretation_task_candidates(self) -> None:
        """Multilingual interpretation candidate affinity."""
        registry = ModelRegistry()
        candidates = registry.get_candidates_for_task(TaskType.MULTILINGUAL_INTERPRETATION)
        names = [c.candidate_name for c in candidates]
        assert "Qwen3.8-27B" in names

    def test_user_explanation_task_candidates(self) -> None:
        """User-facing explanation candidate affinity."""
        registry = ModelRegistry()
        candidates = registry.get_candidates_for_task(TaskType.USER_EXPLANATION)
        names = [c.candidate_name for c in candidates]
        assert "GPT-OSS 20B" in names


class TestMultiLLMConfiguration:
    """Test MultiLLMSettings loading and synchronization."""

    def test_settings_load_with_empty_environment(self) -> None:
        """MultiLLMSettings loads without error when all API keys are absent."""
        settings = MultiLLMSettings(
            groq_api_key=None,
            together_api_key=None,
            openrouter_api_key=None,
            deepseek_api_key=None,
            zai_api_key=None,
        )
        assert settings.groq_api_key is None
        assert settings.has_provider_credentials(ProviderType.GROQ) is False
        assert settings.has_provider_credentials(ProviderType.DEEPSEEK) is False

    def test_settings_sync_updates_credential_status_only(self) -> None:
        """Configuring an API key sets credentials to CONFIGURED but existence stays UNVERIFIED."""
        settings = MultiLLMSettings(
            groq_api_key="gsk-test-mock-key",
            docustruct_model_gpt_oss_20b_id="gpt-oss-20b-chat",
        )
        registry = ModelRegistry(settings=settings)
        candidate = registry.get_candidate("GPT-OSS 20B")
        assert candidate is not None

        # Credentials should now be CONFIGURED
        assert candidate.verification_status.credentials == ConfigurationCredentialStatus.CONFIGURED

        # Exact model ID updated from override
        assert candidate.exact_model_id == "gpt-oss-20b-chat"

        # Crucial invariant: Model existence must remain UNVERIFIED until probe
        assert candidate.verification_status.existence == ModelExistenceStatus.UNVERIFIED
        assert candidate.verification_status.is_operational is False
