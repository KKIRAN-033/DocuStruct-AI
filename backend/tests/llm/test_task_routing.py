"""DocuStruct AI — Task Routing & Capability Matching Integration Tests.

Validates:
    - Routing resolution across all 7 task types with configured priorities.
    - Modality guards rejecting text-only candidates for visual review tasks.
    - Strict isolation of disabled, unverified, uncredentialed, or untested candidates.
    - Fallback candidate chain prioritization.
    - Graceful empty-chain resolution for deterministic continuation.
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
from app.llm.models import (
    CandidateModel,
    ModelVerificationStatus,
    TimeoutRetryPolicy,
)
from app.llm.registry import ModelRegistry
from app.llm.router import (
    TASK_CANDIDATE_PREFERENCES,
    TaskRouter,
    evaluate_candidate_eligibility,
)


def _make_operational_candidate(
    name: str,
    provider: ProviderType,
    exact_id: str,
    tasks: list[TaskType],
    modalities: list[Modality] | None = None,
    priority: int = 1,
    fallback_eligibility: bool = True,
) -> CandidateModel:
    """Helper creating a candidate model with all operational criteria satisfied."""
    return CandidateModel(
        candidate_name=name,
        exact_model_id=exact_id,
        provider=provider,
        supported_modalities=modalities or [Modality.TEXT],
        supported_tasks=tasks,
        configuration_key=f"DOCUSTRUCT_MODEL_{name.replace(' ', '_').upper()}_ID",
        enabled_state=True,
        verification_status=ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        ),
        routing_priority=priority,
        timeout_retry_policy=TimeoutRetryPolicy(timeout_seconds=25.0, max_retries=2),
        fallback_eligibility=fallback_eligibility,
    )


class TestTaskRoutingPriorities:
    """Validate routing resolution across all 7 task types."""

    def test_routing_preferences_complete_for_all_tasks(self) -> None:
        """Confirm all seven discrete tasks have documented preference lists."""
        assert len(TASK_CANDIDATE_PREFERENCES) == 7
        for task in TaskType:
            assert task in TASK_CANDIDATE_PREFERENCES
            assert len(TASK_CANDIDATE_PREFERENCES[task]) >= 1

    def test_routine_classification_routing_chain(self) -> None:
        """ROUTINE_CLASSIFICATION resolves GPT-OSS 20B -> DeepSeek V4.1 Flash -> Llama 4 Scout."""
        registry = ModelRegistry()
        for name in ["GPT-OSS 20B", "DeepSeek V4.1 Flash", "Llama 4 Scout"]:
            c = registry.get_candidate(name)
            assert c is not None
            c.enabled_state = True
            c.exact_model_id = f"verified/{name.lower().replace(' ', '-')}"
            c.verification_status = ModelVerificationStatus(
                existence=ModelExistenceStatus.CONFIRMED,
                provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.PASSED,
            )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        names = [c.candidate_name for c in chain]
        assert names == ["GPT-OSS 20B", "DeepSeek V4.1 Flash", "Llama 4 Scout"]

    def test_complex_table_interpretation_routing_chain(self) -> None:
        """COMPLEX_TABLE_INTERPRETATION resolves DeepSeek V4.1 Flash -> GPT-OSS 120B -> GLM-5.3-Flash."""
        registry = ModelRegistry()
        for name in ["DeepSeek V4.1 Flash", "GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"]:
            c = registry.get_candidate(name)
            assert c is not None
            c.enabled_state = True
            c.exact_model_id = f"verified/{name.lower().replace(' ', '-')}"
            c.verification_status = ModelVerificationStatus(
                existence=ModelExistenceStatus.CONFIRMED,
                provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.PASSED,
            )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.COMPLEX_TABLE_INTERPRETATION)
        names = [c.candidate_name for c in chain]
        assert names == ["DeepSeek V4.1 Flash", "GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"]

    def test_conflicting_hypotheses_routing_chain(self) -> None:
        """CONFLICTING_HYPOTHESES resolves GPT-OSS 120B -> GLM-5.3-Flash through Z.ai."""
        registry = ModelRegistry()
        for name in ["GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"]:
            c = registry.get_candidate(name)
            assert c is not None
            c.enabled_state = True
            c.exact_model_id = f"verified/{name.lower().replace(' ', '-')}"
            c.verification_status = ModelVerificationStatus(
                existence=ModelExistenceStatus.CONFIRMED,
                provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.PASSED,
            )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.CONFLICTING_HYPOTHESES)
        names = [c.candidate_name for c in chain]
        assert names == ["GPT-OSS 120B", "GLM-5.3-Flash through Z.ai"]

    def test_correction_proposal_routing_chain(self) -> None:
        """CORRECTION_PROPOSAL resolves GPT-OSS 20B -> DeepSeek V4.1 Flash."""
        registry = ModelRegistry()
        for name in ["GPT-OSS 20B", "DeepSeek V4.1 Flash"]:
            c = registry.get_candidate(name)
            assert c is not None
            c.enabled_state = True
            c.exact_model_id = f"verified/{name.lower().replace(' ', '-')}"
            c.verification_status = ModelVerificationStatus(
                existence=ModelExistenceStatus.CONFIRMED,
                provider_availability=ProviderAvailabilityStatus.AVAILABLE,
                credentials=ConfigurationCredentialStatus.CONFIGURED,
                test_result=IntegrationTestStatus.PASSED,
            )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.CORRECTION_PROPOSAL)
        names = [c.candidate_name for c in chain]
        assert names == ["GPT-OSS 20B", "DeepSeek V4.1 Flash"]

    def test_multilingual_interpretation_routing_chain(self) -> None:
        """MULTILINGUAL_INTERPRETATION resolves Qwen3.8-27B."""
        registry = ModelRegistry()
        c = registry.get_candidate("Qwen3.8-27B")
        assert c is not None
        c.enabled_state = True
        c.exact_model_id = "verified/qwen3.8-27b"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.MULTILINGUAL_INTERPRETATION)
        assert len(chain) == 1
        assert chain[0].candidate_name == "Qwen3.8-27B"

    def test_user_explanation_routing_chain(self) -> None:
        """USER_EXPLANATION resolves GPT-OSS 20B."""
        registry = ModelRegistry()
        c = registry.get_candidate("GPT-OSS 20B")
        assert c is not None
        c.enabled_state = True
        c.exact_model_id = "verified/gpt-oss-20b"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.USER_EXPLANATION)
        assert len(chain) == 1
        assert chain[0].candidate_name == "GPT-OSS 20B"


class TestCapabilityMismatchGuards:
    """Validate strict rejection of mismatched tasks or modalities."""

    def test_text_only_models_rejected_for_visual_table_review(self) -> None:
        """Text-only candidates must be rejected for VISUAL_TABLE_REVIEW."""
        text_only_models = [
            ("GPT-OSS 20B", ProviderType.GROQ),
            ("GPT-OSS 120B", ProviderType.TOGETHER),
            ("DeepSeek V4.1 Flash", ProviderType.DEEPSEEK),
            ("GLM-5.3-Flash through Z.ai", ProviderType.ZAI),
        ]
        for name, provider in text_only_models:
            cand = _make_operational_candidate(
                name=name,
                provider=provider,
                exact_id="test-id",
                tasks=[TaskType.VISUAL_TABLE_REVIEW, TaskType.ROUTINE_CLASSIFICATION],
                modalities=[Modality.TEXT],  # TEXT ONLY
            )
            eligible, reason = evaluate_candidate_eligibility(
                candidate=cand,
                task=TaskType.VISUAL_TABLE_REVIEW,
                requires_vision=True,
            )
            assert eligible is False
            assert "VISION" in reason

    def test_vision_candidate_accepted_when_modality_confirmed(self) -> None:
        """Candidates with confirmed Modality.VISION are accepted for visual tasks."""
        cand = _make_operational_candidate(
            name="Qwen3.8-27B",
            provider=ProviderType.TOGETHER,
            exact_id="qwen-vision-v1",
            tasks=[TaskType.VISUAL_TABLE_REVIEW],
            modalities=[Modality.TEXT, Modality.VISION],
        )
        eligible, reason = evaluate_candidate_eligibility(
            candidate=cand,
            task=TaskType.VISUAL_TABLE_REVIEW,
            requires_vision=True,
        )
        assert eligible is True
        assert reason == "Eligible"

    def test_unsupported_task_rejection(self) -> None:
        """Candidate is rejected when task is not in its supported_tasks list."""
        cand = _make_operational_candidate(
            name="GPT-OSS 20B",
            provider=ProviderType.GROQ,
            exact_id="gpt-oss-20b",
            tasks=[TaskType.ROUTINE_CLASSIFICATION],  # Does NOT support MULTILINGUAL
        )
        eligible, reason = evaluate_candidate_eligibility(
            candidate=cand,
            task=TaskType.MULTILINGUAL_INTERPRETATION,
        )
        assert eligible is False
        assert "not supported" in reason.lower()


class TestUnverifiedCandidateIsolation:
    """Validate that unverified or disabled candidates are never placed in execution chains."""

    def test_disabled_candidate_never_routed(self) -> None:
        """Disabled candidate (enabled_state=False) is never returned in execution chain."""
        registry = ModelRegistry()
        c = registry.get_candidate("GPT-OSS 20B")
        assert c is not None
        c.enabled_state = False  # Explicitly disabled
        c.exact_model_id = "real/model-id"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        assert "GPT-OSS 20B" not in [x.candidate_name for x in chain]

    def test_unverified_model_id_never_routed(self) -> None:
        """Candidate with exact_model_id='UNVERIFIED' is never returned in execution chain."""
        registry = ModelRegistry()
        c = registry.get_candidate("GPT-OSS 20B")
        assert c is not None
        c.enabled_state = True
        c.exact_model_id = "UNVERIFIED"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        assert "GPT-OSS 20B" not in [x.candidate_name for x in chain]

    def test_missing_credentials_never_routed(self) -> None:
        """Candidate with missing credentials is never returned in execution chain."""
        registry = ModelRegistry()
        c = registry.get_candidate("GPT-OSS 20B")
        assert c is not None
        c.enabled_state = True
        c.exact_model_id = "real/model-id"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        assert "GPT-OSS 20B" not in [x.candidate_name for x in chain]

    def test_untested_probe_never_routed(self) -> None:
        """Candidate with untested integration probe is never returned in execution chain."""
        registry = ModelRegistry()
        c = registry.get_candidate("GPT-OSS 20B")
        assert c is not None
        c.enabled_state = True
        c.exact_model_id = "real/model-id"
        c.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.UNTESTED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        assert "GPT-OSS 20B" not in [x.candidate_name for x in chain]

    def test_default_empty_registry_returns_empty_chain_for_all_tasks(self) -> None:
        """In standard unconfigured environment, all 7 tasks resolve to empty chains."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        router = TaskRouter(settings=settings)
        for task in TaskType:
            chain = router.resolve_execution_chain(task)
            assert chain == [], f"Expected empty chain for unconfigured {task.value}"
