"""DocuStruct AI — TaskRouter & BoundedFallbackEngine Tests.

Validates:
    - Initial candidate preferences for all 7 task types.
    - 8-point eligibility checks (enabled state, exact model ID, credentials, existence,
      provider reachability, integration test status, task affinity, vision modality).
    - Text-only candidate rejection for vision-required tasks.
    - Bounded fallback execution (max_fallbacks=2, max attempts=3).
    - Cycle prevention avoiding duplicate invocations in a single chain.
    - Error reason taxonomy (auth, timeout, rate-limit, server, schema error).
    - Safe deterministic continuation without uncaught exceptions.
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
from app.llm.exceptions import (
    ModelNotFoundError,
    ProviderAuthError,
    ProviderServiceUnavailableError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.fallback import (
    REASON_AUTH_ERROR,
    REASON_CYCLE_PREVENTED,
    REASON_MAX_FALLBACKS_EXCEEDED,
    REASON_RATE_LIMIT,
    REASON_SCHEMA_ERROR,
    REASON_TIMEOUT,
    REASON_UNAVAILABLE,
    BoundedFallbackEngine,
    FallbackResult,
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


def _make_candidate(
    name: str,
    provider: ProviderType = ProviderType.GROQ,
    exact_id: str = "mock-model-v1",
    tasks: list[TaskType] | None = None,
    modalities: list[Modality] | None = None,
    enabled: bool = True,
    existence: ModelExistenceStatus = ModelExistenceStatus.CONFIRMED,
    availability: ProviderAvailabilityStatus = ProviderAvailabilityStatus.AVAILABLE,
    credentials: ConfigurationCredentialStatus = ConfigurationCredentialStatus.CONFIGURED,
    test_result: IntegrationTestStatus = IntegrationTestStatus.PASSED,
) -> CandidateModel:
    """Helper creating a test candidate with fully specified status."""
    return CandidateModel(
        candidate_name=name,
        exact_model_id=exact_id,
        provider=provider,
        supported_modalities=modalities or [Modality.TEXT],
        supported_tasks=tasks or [TaskType.ROUTINE_CLASSIFICATION],
        configuration_key=f"DOCUSTRUCT_MODEL_{name.replace(' ', '_').upper()}_ID",
        enabled_state=enabled,
        verification_status=ModelVerificationStatus(
            existence=existence,
            provider_availability=availability,
            credentials=credentials,
            test_result=test_result,
        ),
        routing_priority=1,
        timeout_retry_policy=TimeoutRetryPolicy(timeout_seconds=10.0, max_retries=2),
        fallback_eligibility=True,
    )


# ── 1. Preference Ordering Tests ─────────────────────────────────────────────


class TestTaskCandidatePreferences:
    """Validate declared preference orderings across all seven task types."""

    def test_all_seven_task_types_have_preferences(self) -> None:
        """Verify that every TaskType has an explicit preference list."""
        for task in TaskType:
            prefs = TASK_CANDIDATE_PREFERENCES.get(task)
            assert prefs is not None, f"Missing preferences for {task.value}"
            assert len(prefs) >= 1, f"Empty preference list for {task.value}"

    def test_specific_task_preference_names(self) -> None:
        """Confirm exact candidate preference lists per the multi-LLM architecture specification."""
        assert TASK_CANDIDATE_PREFERENCES[TaskType.ROUTINE_CLASSIFICATION] == [
            "GPT-OSS 20B",
            "DeepSeek V4.1 Flash",
            "Llama 4 Scout",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.COMPLEX_TABLE_INTERPRETATION] == [
            "DeepSeek V4.1 Flash",
            "GPT-OSS 120B",
            "GLM-5.3-Flash through Z.ai",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.CONFLICTING_HYPOTHESES] == [
            "GPT-OSS 120B",
            "GLM-5.3-Flash through Z.ai",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.CORRECTION_PROPOSAL] == [
            "GPT-OSS 20B",
            "DeepSeek V4.1 Flash",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.MULTILINGUAL_INTERPRETATION] == [
            "Qwen3.8-27B",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.VISUAL_TABLE_REVIEW] == [
            "Qwen3.8-27B",
            "Llama 4 Scout",
            "Gemma 4",
        ]
        assert TASK_CANDIDATE_PREFERENCES[TaskType.USER_EXPLANATION] == [
            "GPT-OSS 20B",
        ]


# ── 2. Pre-flight Eligibility Check Tests ────────────────────────────────────


class TestCandidateEligibilityChecks:
    """Validate 8-point pre-flight eligibility validation."""

    def test_fully_operational_candidate_is_eligible(self) -> None:
        """A candidate meeting all 8 criteria is marked eligible."""
        cand = _make_candidate("GPT-OSS 20B", tasks=[TaskType.ROUTINE_CLASSIFICATION])
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is True
        assert reason == "Eligible"

    def test_disabled_candidate_is_rejected(self) -> None:
        """Disabled candidate is rejected."""
        cand = _make_candidate("GPT-OSS 20B", enabled=False)
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "disabled" in reason.lower()

    def test_unverified_model_id_is_rejected(self) -> None:
        """Exact model ID 'UNVERIFIED' is rejected."""
        cand = _make_candidate("GPT-OSS 20B", exact_id="UNVERIFIED")
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "UNVERIFIED" in reason

    def test_missing_credentials_is_rejected(self) -> None:
        """Missing credentials rejects candidate."""
        cand = _make_candidate(
            "GPT-OSS 20B",
            credentials=ConfigurationCredentialStatus.MISSING_CREDENTIALS,
        )
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "credentials" in reason.lower()

    def test_unverified_model_existence_is_rejected(self) -> None:
        """Model with existence=UNVERIFIED is rejected."""
        cand = _make_candidate("GPT-OSS 20B", existence=ModelExistenceStatus.UNVERIFIED)
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "existence" in reason.lower()

    def test_unavailable_provider_is_rejected(self) -> None:
        """Model with provider_availability=UNAVAILABLE is rejected."""
        cand = _make_candidate(
            "GPT-OSS 20B",
            availability=ProviderAvailabilityStatus.UNAVAILABLE,
        )
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "availability" in reason.lower()

    def test_untested_or_failed_probe_is_rejected(self) -> None:
        """Model with integration_test != PASSED is rejected."""
        cand = _make_candidate("GPT-OSS 20B", test_result=IntegrationTestStatus.UNTESTED)
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False
        assert "integration test" in reason.lower()

        cand_failed = _make_candidate("GPT-OSS 20B", test_result=IntegrationTestStatus.FAILED)
        eligible, reason = evaluate_candidate_eligibility(cand_failed, TaskType.ROUTINE_CLASSIFICATION)
        assert eligible is False

    def test_unsupported_task_is_rejected(self) -> None:
        """Candidate that does not support the targeted task is rejected."""
        cand = _make_candidate("GPT-OSS 20B", tasks=[TaskType.ROUTINE_CLASSIFICATION])
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.COMPLEX_TABLE_INTERPRETATION)
        assert eligible is False
        assert "not supported" in reason.lower()

    def test_text_only_candidate_rejected_for_vision_task(self) -> None:
        """Text-only candidate is strictly rejected for VISUAL_TABLE_REVIEW."""
        cand = _make_candidate(
            "Qwen3.8-27B",
            tasks=[TaskType.VISUAL_TABLE_REVIEW],
            modalities=[Modality.TEXT],  # Vision unverified
        )
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.VISUAL_TABLE_REVIEW)
        assert eligible is False
        assert "VISION" in reason

    def test_vision_candidate_accepted_for_vision_task(self) -> None:
        """Candidate with verified Modality.VISION is accepted for VISUAL_TABLE_REVIEW."""
        cand = _make_candidate(
            "Qwen3.8-27B",
            tasks=[TaskType.VISUAL_TABLE_REVIEW],
            modalities=[Modality.TEXT, Modality.VISION],
        )
        eligible, reason = evaluate_candidate_eligibility(cand, TaskType.VISUAL_TABLE_REVIEW)
        assert eligible is True


# ── 3. Execution Chain Resolution Tests ──────────────────────────────────────


class TestExecutionChainResolution:
    """Validate TaskRouter execution chain resolution and deterministic fallback."""

    def test_empty_chain_when_all_candidates_unverified(self) -> None:
        """Default unverified registry returns empty chain, triggering deterministic path."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        router = TaskRouter(settings=settings)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        assert chain == []

    def test_chain_contains_eligible_candidates_in_preference_order(self) -> None:
        """When multiple candidates are operational, chain orders them by preference."""
        registry = ModelRegistry()
        # Enable and verify two candidates: DeepSeek V4.1 Flash and GPT-OSS 20B
        c1 = registry.get_candidate("GPT-OSS 20B")
        assert c1 is not None
        c1.enabled_state = True
        c1.exact_model_id = "openai/gpt-oss-20b"
        c1.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        c2 = registry.get_candidate("DeepSeek V4.1 Flash")
        assert c2 is not None
        c2.enabled_state = True
        c2.exact_model_id = "deepseek-v4.1-flash"
        c2.verification_status = ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        )

        router = TaskRouter(registry=registry)
        chain = router.resolve_execution_chain(TaskType.ROUTINE_CLASSIFICATION)
        # For ROUTINE_CLASSIFICATION, preference is [GPT-OSS 20B, DeepSeek V4.1 Flash, Llama 4 Scout]
        assert len(chain) == 2
        assert chain[0].candidate_name == "GPT-OSS 20B"
        assert chain[1].candidate_name == "DeepSeek V4.1 Flash"


# ── 4. Bounded Fallback Engine Tests ──────────────────────────────────────────


class TestBoundedFallbackEngine:
    """Validate bounded retries, cycle prevention, and error taxonomy."""

    @pytest.mark.asyncio
    async def test_primary_candidate_success_no_fallback(self) -> None:
        """Successful primary candidate requires zero fallback hops."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_candidate("Model-1")
        c2 = _make_candidate("Model-2")

        async def _mock_invoke(c: CandidateModel) -> str:
            return f"Result from {c.candidate_name}"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_mock_invoke,
        )

        assert res.success is True
        assert res.result == "Result from Model-1"
        assert res.fallback_hops == 0
        assert res.fallback_to_deterministic is False
        assert len(res.audit_trail) == 1
        assert res.audit_trail[0].candidate_name == "Model-1"
        assert res.audit_trail[0].success is True

    @pytest.mark.asyncio
    async def test_primary_fails_secondary_succeeds(self) -> None:
        """When primary fails with 5xx, engine falls back to secondary candidate."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_candidate("Model-1")
        c2 = _make_candidate("Model-2")

        async def _mock_invoke(c: CandidateModel) -> str:
            if c.candidate_name == "Model-1":
                raise ProviderServiceUnavailableError("Model 1 service outage", provider="GROQ")
            return "Success from Model-2"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_mock_invoke,
        )

        assert res.success is True
        assert res.result == "Success from Model-2"
        assert res.fallback_hops == 1
        assert res.candidate_used == c2
        assert len(res.audit_trail) == 2
        assert res.audit_trail[0].error_reason == REASON_UNAVAILABLE
        assert res.audit_trail[1].success is True

    @pytest.mark.asyncio
    async def test_fallback_exhaustion_triggers_deterministic(self) -> None:
        """When all candidates fail, engine returns fallback_to_deterministic=True without uncaught error."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_candidate("Model-1")
        c2 = _make_candidate("Model-2")

        async def _mock_invoke(c: CandidateModel) -> str:
            raise ProviderTimeoutError(f"Timeout on {c.candidate_name}")

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_mock_invoke,
        )

        assert res.success is False
        assert res.result is None
        assert res.fallback_to_deterministic is True
        assert res.fallback_hops == 2
        assert len(res.audit_trail) == 2
        assert res.audit_trail[0].error_reason == REASON_TIMEOUT
        assert res.audit_trail[1].error_reason == REASON_TIMEOUT

    @pytest.mark.asyncio
    async def test_max_fallbacks_bound_capped_at_two(self) -> None:
        """Max fallbacks = 2 caps execution at 3 total attempts even if more candidates exist."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        candidates = [_make_candidate(f"Model-{i}") for i in range(1, 6)]
        attempted: list[str] = []

        async def _mock_invoke(c: CandidateModel) -> str:
            attempted.append(c.candidate_name)
            raise RateLimitExceededError("Rate limited", retry_after_seconds=5.0)

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=candidates,
            invoke_fn=_mock_invoke,
        )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        # Only 3 candidates attempted (1 initial + 2 fallbacks)
        assert attempted == ["Model-1", "Model-2", "Model-3"]
        assert len(res.audit_trail) == 4  # 3 attempts + 1 cap halt record
        assert res.audit_trail[3].error_reason == REASON_MAX_FALLBACKS_EXCEEDED

    @pytest.mark.asyncio
    async def test_cycle_prevention_skips_duplicate_candidate(self) -> None:
        """A candidate appearing twice in the list is only invoked once."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_candidate("Model-1")
        c2 = _make_candidate("Model-2")
        # List contains duplicate c1
        candidates = [c1, c1, c2]
        attempted: list[str] = []

        async def _mock_invoke(c: CandidateModel) -> str:
            attempted.append(c.candidate_name)
            if c.candidate_name == "Model-1":
                raise ProviderAuthError("Auth failed")
            return "Success from Model-2"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=candidates,
            invoke_fn=_mock_invoke,
        )

        assert res.success is True
        assert res.result == "Success from Model-2"
        # c1 was invoked once, second c1 skipped by cycle detector, then c2 succeeded
        assert attempted == ["Model-1", "Model-2"]
        # Audit trail records attempt 1 failure, cycle detection skip, and attempt 2 success
        reasons = [rec.error_reason for rec in res.audit_trail]
        assert REASON_CYCLE_PREVENTED in reasons

    @pytest.mark.asyncio
    async def test_error_taxonomy_categorization(self) -> None:
        """Verify distinct typed reason codes for all failure categories."""
        engine = BoundedFallbackEngine(max_fallbacks=5)
        c_auth = _make_candidate("C-Auth")
        c_time = _make_candidate("C-Time")
        c_rate = _make_candidate("C-Rate")
        c_schema = _make_candidate("C-Schema")

        async def _mock_invoke(c: CandidateModel) -> str:
            if c.candidate_name == "C-Auth":
                raise ProviderAuthError("Bad key")
            elif c.candidate_name == "C-Time":
                raise ProviderTimeoutError("Timeout")
            elif c.candidate_name == "C-Rate":
                raise RateLimitExceededError("Rate limit", retry_after_seconds=3.0)
            elif c.candidate_name == "C-Schema":
                raise SchemaValidationError("Invalid schema")
            return "OK"

        res = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c_auth, c_time, c_rate, c_schema],
            invoke_fn=_mock_invoke,
        )

        assert res.success is False
        assert res.audit_trail[0].error_reason == REASON_AUTH_ERROR
        assert res.audit_trail[1].error_reason == REASON_TIMEOUT
        assert res.audit_trail[2].error_reason == REASON_RATE_LIMIT
        assert res.audit_trail[2].retry_after_seconds == 3.0
        assert res.audit_trail[3].error_reason == REASON_SCHEMA_ERROR

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_deterministic_immediately(self) -> None:
        """Empty candidate list immediately flags fallback_to_deterministic=True."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        res = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[],
            invoke_fn=lambda c: None,
        )
        assert res.success is False
        assert res.fallback_to_deterministic is True
        assert res.fallback_hops == 0
