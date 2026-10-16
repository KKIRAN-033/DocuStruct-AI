"""DocuStruct AI — Provider Failure Modes & Bounded Fallback Tests.

Validates:
    - Accurate error mapping for HTTP 401, 404, 429 (Retry-After), 500/503,
      connect/read timeouts, connection refusals, and malformed responses.
    - BoundedFallbackEngine handling of diverse failure modes.
    - Fallback ceiling: max_fallbacks=2 caps execution at 3 attempts.
    - Cycle prevention avoiding duplicate candidate invocations in a chain.
    - Graceful deterministic hand-off on complete fallback exhaustion.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

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
)
from app.llm.fallback import (
    REASON_AUTH_ERROR,
    REASON_CYCLE_PREVENTED,
    REASON_MAX_FALLBACKS_EXCEEDED,
    REASON_RATE_LIMIT,
    REASON_SERVER_ERROR,
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
from app.llm.providers.groq import GroqProviderAdapter
from tests.llm.conftest import create_mock_client


def _make_test_candidate(name: str, provider: ProviderType = ProviderType.GROQ) -> CandidateModel:
    """Helper creating a test candidate model."""
    return CandidateModel(
        candidate_name=name,
        exact_model_id=f"model/{name.lower()}",
        provider=provider,
        supported_modalities=[Modality.TEXT],
        supported_tasks=[TaskType.ROUTINE_CLASSIFICATION],
        configuration_key=f"DOCUSTRUCT_MODEL_{name.upper()}_ID",
        enabled_state=True,
        verification_status=ModelVerificationStatus(
            existence=ModelExistenceStatus.CONFIRMED,
            provider_availability=ProviderAvailabilityStatus.AVAILABLE,
            credentials=ConfigurationCredentialStatus.CONFIGURED,
            test_result=IntegrationTestStatus.PASSED,
        ),
        routing_priority=1,
        timeout_retry_policy=TimeoutRetryPolicy(timeout_seconds=5.0, max_retries=2),
        fallback_eligibility=True,
    )


# ── 1. Provider Adapter Error Mapping Tests ──────────────────────────────────


class TestProviderErrorMapping:
    """Validate accurate typed error mapping on HTTP failure status codes."""

    @pytest.mark.asyncio
    async def test_http_401_raises_provider_auth_error(self) -> None:
        """HTTP 401 returns ProviderAuthError."""
        mock_client, _ = create_mock_client(status_code=401, text="Invalid API Key")
        adapter = GroqProviderAdapter(api_key="bad-key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderAuthError):
                await adapter.complete(model_id="test-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_http_404_raises_model_not_found_error(self) -> None:
        """HTTP 404 returns ModelNotFoundError."""
        mock_client, _ = create_mock_client(status_code=404, text="Model not found")
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ModelNotFoundError):
                await adapter.complete(model_id="nonexistent-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_http_429_parses_retry_after_header(self) -> None:
        """HTTP 429 extracts Retry-After seconds and raises RateLimitExceededError."""
        mock_client, _ = create_mock_client(
            status_code=429,
            text="Rate limit exceeded",
            headers={"retry-after": "4.5"},
        )
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RateLimitExceededError) as exc_info:
                await adapter.complete(model_id="test-model", prompt="hello")
        assert exc_info.value.retry_after_seconds == 4.5

    @pytest.mark.asyncio
    async def test_http_500_raises_provider_service_unavailable(self) -> None:
        """HTTP 500 server error raises ProviderServiceUnavailableError."""
        mock_client, _ = create_mock_client(status_code=500, text="Internal Server Error")
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete(model_id="test-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_http_503_raises_provider_service_unavailable(self) -> None:
        """HTTP 503 outage raises ProviderServiceUnavailableError."""
        mock_client, _ = create_mock_client(status_code=503, text="Service Unavailable")
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete(model_id="test-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_read_timeout_raises_provider_timeout_error(self) -> None:
        """Read timeout raises ProviderTimeoutError."""
        mock_client, _ = create_mock_client(side_effect=httpx.ReadTimeout("Read timed out"))
        adapter = GroqProviderAdapter(api_key="key", timeout_seconds=1.0)
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderTimeoutError):
                await adapter.complete(model_id="test-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_connect_error_raises_provider_service_unavailable(self) -> None:
        """Network connection refusal raises ProviderServiceUnavailableError."""
        mock_client, _ = create_mock_client(side_effect=httpx.ConnectError("Connection refused"))
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderServiceUnavailableError):
                await adapter.complete(model_id="test-model", prompt="hello")

    @pytest.mark.asyncio
    async def test_malformed_json_response_raises_multi_llm_error(self) -> None:
        """HTTP 200 with non-JSON body raises MultiLLMError."""
        mock_client, _ = create_mock_client(status_code=200, text="<HTML>Not JSON</HTML>")
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(MultiLLMError) as exc_info:
                await adapter.complete(model_id="test-model", prompt="hello")
        assert "Failed to parse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_choices_payload_raises_multi_llm_error(self) -> None:
        """HTTP 200 with missing choices array raises MultiLLMError."""
        mock_client, _ = create_mock_client(status_code=200, json_data={"unexpected": "structure"})
        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(MultiLLMError) as exc_info:
                await adapter.complete(model_id="test-model", prompt="hello")
        assert "choices" in str(exc_info.value)


# ── 2. Fallback Engine Integration with Failure Modes ────────────────────────


class TestFallbackEngineFailureHandling:
    """Validate BoundedFallbackEngine behavior when facing real failure modes."""

    @pytest.mark.asyncio
    async def test_auth_failure_triggers_fallback_to_secondary(self) -> None:
        """Auth error on primary model falls back to secondary model."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Primary-Model")
        c2 = _make_test_candidate("Secondary-Model")

        async def _invoke(candidate: CandidateModel) -> str:
            if candidate.candidate_name == "Primary-Model":
                raise ProviderAuthError("Invalid API key for primary", provider="GROQ")
            return "Secondary model succeeded"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.result == "Secondary model succeeded"
        assert res.fallback_hops == 1
        assert res.candidate_used == c2
        assert res.audit_trail[0].error_reason == REASON_AUTH_ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_failure_triggers_fallback_preserving_retry_after(self) -> None:
        """Rate limit on primary model records retry_after and falls back to secondary."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Primary-Model")
        c2 = _make_test_candidate("Secondary-Model")

        async def _invoke(candidate: CandidateModel) -> str:
            if candidate.candidate_name == "Primary-Model":
                raise RateLimitExceededError("Rate limit exceeded", retry_after_seconds=5.0)
            return "Secondary succeeded"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.result == "Secondary succeeded"
        assert res.audit_trail[0].error_reason == REASON_RATE_LIMIT
        assert res.audit_trail[0].retry_after_seconds == 5.0

    @pytest.mark.asyncio
    async def test_timeout_failure_triggers_fallback(self) -> None:
        """Timeout on primary model falls back to secondary."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Primary-Model")
        c2 = _make_test_candidate("Secondary-Model")

        async def _invoke(candidate: CandidateModel) -> str:
            if candidate.candidate_name == "Primary-Model":
                raise ProviderTimeoutError("Request timed out after 5.0s")
            return "Secondary succeeded"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.result == "Secondary succeeded"
        assert res.audit_trail[0].error_reason == REASON_TIMEOUT

    @pytest.mark.asyncio
    async def test_server_error_triggers_fallback(self) -> None:
        """5xx server error on primary model falls back to secondary."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Primary-Model")
        c2 = _make_test_candidate("Secondary-Model")

        async def _invoke(candidate: CandidateModel) -> str:
            if candidate.candidate_name == "Primary-Model":
                raise ProviderServiceUnavailableError("503 Service Unavailable")
            return "Secondary succeeded"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.result == "Secondary succeeded"
        assert res.audit_trail[0].error_reason == REASON_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_all_candidates_fail_triggers_deterministic_continuation(self) -> None:
        """When all candidates fail, engine returns deterministic continuation cleanly."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Candidate-1")
        c2 = _make_test_candidate("Candidate-2")

        async def _invoke(candidate: CandidateModel) -> str:
            raise ProviderServiceUnavailableError(f"500 on {candidate.candidate_name}")

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        assert res.fallback_hops == 2
        assert len(res.audit_trail) == 2

    @pytest.mark.asyncio
    async def test_max_fallbacks_two_caps_at_three_attempts(self) -> None:
        """Engine caps attempts at 3 (1 primary + 2 fallbacks) when 5 candidates are present."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        candidates = [_make_test_candidate(f"Candidate-{i}") for i in range(1, 6)]
        attempted: list[str] = []

        async def _invoke(candidate: CandidateModel) -> str:
            attempted.append(candidate.candidate_name)
            raise ProviderTimeoutError(f"Timeout on {candidate.candidate_name}")

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=candidates,
            invoke_fn=_invoke,
        )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        # Only 3 candidates attempted
        assert attempted == ["Candidate-1", "Candidate-2", "Candidate-3"]
        # Audit trail contains 3 attempt records + 1 ceiling halt record
        assert len(res.audit_trail) == 4
        assert res.audit_trail[3].error_reason == REASON_MAX_FALLBACKS_EXCEEDED

    @pytest.mark.asyncio
    async def test_cycle_prevention_skips_repeated_candidate(self) -> None:
        """Candidate appearing multiple times in chain is skipped on repeat."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_test_candidate("Candidate-1")
        c2 = _make_test_candidate("Candidate-2")
        # List repeats c1
        chain = [c1, c1, c2]
        attempted: list[str] = []

        async def _invoke(candidate: CandidateModel) -> str:
            attempted.append(candidate.candidate_name)
            if candidate.candidate_name == "Candidate-1":
                raise ProviderAuthError("Auth failed")
            return "Success from Candidate-2"

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.ROUTINE_CLASSIFICATION,
            candidates=chain,
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.result == "Success from Candidate-2"
        assert attempted == ["Candidate-1", "Candidate-2"]
        reasons = [r.error_reason for r in res.audit_trail]
        assert REASON_CYCLE_PREVENTED in reasons
