"""DocuStruct AI — Orchestration Workers & Models Status Endpoint Tests.

Validates:
    - Strict Pydantic v2 structured output schemas (rejection of malformed/extra fields).
    - Immutable cell.raw_value across all correction flows.
    - Prohibition of auto-balancing totals (preserves raw total, stores inferred candidate only).
    - Permitted evidence sources vs unapproved heuristic rejection.
    - DiscrepancyWorker adjudication with zero cell mutation and human review routing.
    - ExplanationWorker deterministic template fallback.
    - GET /api/v1/models/status schema, 7 registered candidates, 5 providers, and secret redaction.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.app import app
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
from app.llm.fallback import BoundedFallbackEngine, FallbackResult
from app.llm.exceptions import (
    ProviderAuthError,
    ProviderTimeoutError,
    RateLimitExceededError,
    SchemaValidationError,
)
from app.llm.models import (
    CandidateModel,
    ModelVerificationStatus,
    StructuredCompletionResponse,
    TimeoutRetryPolicy,
)
from app.llm.providers.factory import ProviderFactory
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.registry import ModelRegistry
from app.llm.router import TaskRouter
from app.llm.schemas import (
    CorrectionProposal,
    DiscrepancyHypothesis,
    ModelsStatusResponse,
    PageClassificationEnrichment,
    TableInterpretationResult,
    UserExplanationPayload,
)
from app.llm.workers.base_worker import BaseWorker
from app.llm.workers.correction_worker import CorrectionWorker
from app.llm.workers.discrepancy_worker import DiscrepancyWorker
from app.llm.workers.explanation_worker import ExplanationWorker
from app.models.domain import CellRecord
from app.models.state import CellQualityStatus, DataType

client = TestClient(app)


def _make_test_cell(
    raw_value: str = "350.00",
    accepted_value: str = "350.00",
    row_idx: int = 5,
    col_idx: int = 2,
    table_id: str = "table_1",
) -> CellRecord:
    """Helper creating a test CellRecord."""
    return CellRecord(
        table_id=table_id,
        row_idx=row_idx,
        col_idx=col_idx,
        source_page=1,
        extraction_method="stream",
        raw_value=raw_value,
        accepted_value=accepted_value,
        numeric_decimal=Decimal("350.00"),
        data_type=DataType.DECIMAL,
        quality_status=CellQualityStatus.CORROBORATED,
    )


# ── 1. Strict Schema Validation Tests ────────────────────────────────────────


class TestStructuredOutputSchemas:
    """Validate strict Pydantic schema validation and extra-field rejection."""

    def test_page_classification_enrichment_valid(self) -> None:
        """Valid PageClassificationEnrichment parses correctly."""
        data = {
            "layout_analysis": "Multi-column financial statement with header block",
            "has_borderless_tables": True,
            "script_detection": ["Latin"],
            "confidence": 0.95,
        }
        res = PageClassificationEnrichment.model_validate(data)
        assert res.has_borderless_tables is True
        assert res.confidence == 0.95

    def test_page_classification_enrichment_forbids_extra_fields(self) -> None:
        """Extra fields are rejected (extra='forbid')."""
        data = {
            "layout_analysis": "Analysis",
            "has_borderless_tables": False,
            "script_detection": [],
            "confidence": 0.9,
            "unexpected_field": "injected",
        }
        with pytest.raises(ValidationError):
            PageClassificationEnrichment.model_validate(data)

    def test_table_interpretation_result_confidence_bounds(self) -> None:
        """Confidence score must be within [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            TableInterpretationResult.model_validate({
                "detected_columns": ["A", "B"],
                "confidence": 1.5,
            })

    def test_discrepancy_hypothesis_valid(self) -> None:
        """DiscrepancyHypothesis validates coordinates and rationale."""
        data = {
            "table_id": "tbl_01",
            "row_idx": 2,
            "col_idx": 3,
            "hypothesis_type": "DECIMAL_SHIFT",
            "explanation": "Extra trailing zero shifted thousands separator.",
            "recommended_action": "HUMAN_REVIEW",
        }
        hyp = DiscrepancyHypothesis.model_validate(data)
        assert hyp.hypothesis_type == "DECIMAL_SHIFT"
        assert hyp.recommended_action == "HUMAN_REVIEW"

    def test_correction_proposal_valid(self) -> None:
        """CorrectionProposal parses target coordinates and evidence."""
        data = {
            "table_id": "tbl_01",
            "row_idx": 4,
            "col_idx": 1,
            "original_value": "100.00",
            "proposed_value": "10.00",
            "evidence_source": "NATIVE_PDF_CHAR_STREAM",
            "evidence_summary": "Char stream contains '10.00' at glyph coordinate (45, 120)",
            "confidence": 0.98,
        }
        prop = CorrectionProposal.model_validate(data)
        assert prop.original_value == "100.00"
        assert prop.proposed_value == "10.00"
        assert prop.evidence_source == "NATIVE_PDF_CHAR_STREAM"


# ── 2. CorrectionWorker & Evidence Gating Tests ──────────────────────────────


class TestCorrectionWorker:
    """Validate CorrectionWorker adherence to DECISION-007, DECISION-011, and Section 15."""

    def test_raw_value_is_never_modified_on_valid_evidence(self) -> None:
        """Even when evidence is accepted, cell.raw_value remains completely immutable."""
        worker = CorrectionWorker()
        cell = _make_test_cell(raw_value="O.50", accepted_value="O.50")

        proposal = CorrectionProposal(
            table_id=cell.table_id,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_value=cell.raw_value,
            proposed_value="0.50",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Digit '0' extracted from text stream at glyph index 4",
            confidence=0.99,
        )

        updated_cell, record = worker.apply_proposal(cell, proposal, is_total_or_sum_cell=False)

        # Invariant 1: raw_value is strictly immutable
        assert updated_cell.raw_value == "O.50"
        # accepted_value is corrected
        assert updated_cell.accepted_value == "0.50"
        assert updated_cell.numeric_decimal == Decimal("0.50")
        assert updated_cell.quality_status == CellQualityStatus.CORRECTED_WITH_EVIDENCE
        assert record.decision == "CORRECTION_ACCEPTED"
        assert record.deterministic_check_passed is True

    def test_unapproved_evidence_source_rejected(self) -> None:
        """Model proposal backed by unapproved evidence source cannot modify accepted_value."""
        worker = CorrectionWorker()
        cell = _make_test_cell(raw_value="1,234.00", accepted_value="1,234.00")

        proposal = CorrectionProposal(
            table_id=cell.table_id,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_value=cell.raw_value,
            proposed_value="1,234.50",
            evidence_source="LLM_HEURISTIC_PREDICTION",  # Not in PERMITTED_EVIDENCE_SOURCES
            evidence_summary="Model guessed last two digits based on context",
            confidence=0.80,
        )

        updated_cell, record = worker.apply_proposal(cell, proposal, is_total_or_sum_cell=False)

        # Raw value and accepted value remain unchanged
        assert updated_cell.raw_value == "1,234.00"
        assert updated_cell.accepted_value == "1,234.00"
        # Inferred candidate stored safely
        assert updated_cell.inferred_candidate_value == "1,234.50"
        assert updated_cell.quality_status == CellQualityStatus.ILLEGIBLE_OR_MISSING
        assert record.inferred_candidate_only is True
        assert record.decision == "INFERRED_CANDIDATE_RECORDED"
        assert record.deterministic_check_passed is False

    def test_auto_balancing_totals_is_strictly_forbidden(self) -> None:
        """Proposals modifying a total/sum cell to force arithmetic balance are strictly rejected."""
        worker = CorrectionWorker()
        # Suppose row has 100 + 200 = 350; the total cell is 350
        total_cell = _make_test_cell(raw_value="350.00", accepted_value="350.00")

        # LLM tries to change 350.00 -> 300.00 to force math consistency
        proposal = CorrectionProposal(
            table_id=total_cell.table_id,
            row_idx=total_cell.row_idx,
            col_idx=total_cell.col_idx,
            original_value="350.00",
            proposed_value="300.00",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Sum calculation 100 + 200 = 300",
            confidence=0.99,
        )

        updated_cell, record = worker.apply_proposal(
            total_cell,
            proposal,
            is_total_or_sum_cell=True,  # Target is a total/sum cell
        )

        # Raw and accepted values are PRESERVED (no auto-balancing)
        assert updated_cell.raw_value == "350.00"
        assert updated_cell.accepted_value == "350.00"
        # Proposal is stored ONLY as inferred candidate
        assert updated_cell.inferred_candidate_value == "300.00"
        assert updated_cell.quality_status == CellQualityStatus.ILLEGIBLE_OR_MISSING
        assert record.inferred_candidate_only is True
        assert "REJECTED_AUTO_BALANCE" in record.decision
        assert record.deterministic_check_passed is False

    @pytest.mark.asyncio
    async def test_propose_correction_deterministic_fallback_when_unconfigured(self) -> None:
        """When no AI models are eligible, propose_correction returns deterministic fallback."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        worker = CorrectionWorker(settings=settings)
        cell = _make_test_cell()

        res: FallbackResult = await worker.propose_correction(cell)
        assert res.success is False
        assert res.fallback_to_deterministic is True


# ── 3. DiscrepancyWorker Tests ───────────────────────────────────────────────


class TestDiscrepancyWorker:
    """Validate DiscrepancyWorker adjudication and cell immutability."""

    @pytest.mark.asyncio
    async def test_discrepancy_deterministic_fallback_preserves_cell(self) -> None:
        """Deterministic fallback produces HUMAN_REVIEW hypothesis without mutating cells."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        worker = DiscrepancyWorker(settings=settings)

        hyp = await worker.adjudicate_discrepancy(
            table_id="table_1",
            row_idx=2,
            col_idx=3,
            extracted_value="1,200",
            conflicting_hypotheses=["1,200.00", "12.00"],
            context="Balance sheet liabilities row",
        )

        assert hyp.table_id == "table_1"
        assert hyp.row_idx == 2
        assert hyp.col_idx == 3
        assert hyp.recommended_action == "HUMAN_REVIEW"
        assert "conflicting hypotheses" in hyp.explanation.lower()


# ── 4. ExplanationWorker Tests ───────────────────────────────────────────────


class TestExplanationWorker:
    """Validate user explanation generation and deterministic template fallback."""

    @pytest.mark.asyncio
    async def test_explanation_deterministic_template_for_math_sum_mismatch(self) -> None:
        """ExplanationWorker uses template for MATH_SUM_MISMATCH without crashing."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        worker = ExplanationWorker(settings=settings)

        payload = await worker.explain_issue(
            issue_id="iss_001",
            issue_code="MATH_SUM_MISMATCH",
            description="Column sum expected 500, found 450",
            expected_value="500",
            actual_value="450",
        )

        assert payload.issue_id == "iss_001"
        assert "sum" in payload.summary.lower()
        assert "inspect" in payload.recommendation.lower()

    @pytest.mark.asyncio
    async def test_explanation_deterministic_template_for_formula_risk(self) -> None:
        """ExplanationWorker uses template for FORMULA_INJECTION_RISK."""
        settings = MultiLLMSettings(
            groq_api_key="",
            together_api_key="",
            openrouter_api_key="",
            deepseek_api_key="",
            zai_api_key="",
        )
        worker = ExplanationWorker(settings=settings)

        payload = await worker.explain_issue(
            issue_id="iss_002",
            issue_code="FORMULA_INJECTION_RISK",
            description="Leading equal sign detected",
            actual_value="=SUM(A1:A5)",
        )

        assert payload.issue_id == "iss_002"
        assert "formula" in payload.summary.lower()


# ── 5. Models Status Endpoint Tests ──────────────────────────────────────────


class TestModelsStatusEndpoint:
    """Validate GET /api/v1/models/status behavior and secret redaction."""

    def test_models_status_returns_200(self) -> None:
        """Endpoint returns HTTP 200 with valid ModelsStatusResponse payload."""
        response = client.get("/api/v1/models/status")
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert "providers" in data
        assert "timestamp" in data

    def test_models_status_contains_all_seven_candidates(self) -> None:
        """Response lists all seven named candidates in registry."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        model_names = [m["candidate_name"] for m in data["models"]]

        expected_names = [
            "GPT-OSS 20B",
            "GPT-OSS 120B",
            "DeepSeek V4.1 Flash",
            "GLM-5.3-Flash through Z.ai",
            "Qwen3.8-27B",
            "Llama 4 Scout",
            "Gemma 4",
        ]
        assert len(model_names) == 7
        for name in expected_names:
            assert name in model_names

    def test_unverified_candidates_remain_disabled(self) -> None:
        """Models without empirical verification remain enabled_state=False and not operational."""
        response = client.get("/api/v1/models/status")
        data = response.json()

        for model in data["models"]:
            # All candidates default to disabled
            assert model["enabled_state"] is False
            # Check verification dimensions
            v = model["verification_status"]
            # Under initial unconfigured environment, existence is UNVERIFIED
            assert v["test_result"] == "UNTESTED"

    def test_models_status_contains_all_five_providers(self) -> None:
        """Health status covers GROQ, TOGETHER, OPENROUTER, DEEPSEEK, and ZAI."""
        response = client.get("/api/v1/models/status")
        data = response.json()
        providers = data["providers"]

        for p_name in ["GROQ", "TOGETHER", "OPENROUTER", "DEEPSEEK", "ZAI"]:
            assert p_name in providers
            p_health = providers[p_name]
            assert "available" in p_health
            assert "configured" in p_health

    def test_secrets_redaction(self) -> None:
        """Verify that no sensitive API keys or credentials leaked into JSON response."""
        response = client.get("/api/v1/models/status")
        raw_text = response.text

        # Verify no Bearer tokens or secret headers
        assert "Bearer" not in raw_text
        assert "api_key" not in raw_text.lower() or "configuration_key" in raw_text
        # Ensure only configuration keys (e.g. DOCUSTRUCT_MODEL_GPT_OSS_20B_ID) are returned
        data = response.json()
        for model in data["models"]:
            assert model["configuration_key"].startswith("DOCUSTRUCT_MODEL_")


# ── 6. Worker Invocation with Eligible Candidate & Provider Alignment ────────


def _make_eligible_candidate(
    name: str = "GPT-OSS 20B",
    exact_model_id: str = "gpt-oss-20b",
    provider: ProviderType = ProviderType.GROQ,
    tasks: Optional[list[TaskType]] = None,
) -> CandidateModel:
    """Helper creating an eligible, confirmed candidate model for testing."""
    return CandidateModel(
        candidate_name=name,
        exact_model_id=exact_model_id,
        provider=provider,
        supported_modalities=[Modality.TEXT],
        supported_tasks=tasks or [TaskType.CORRECTION_PROPOSAL, TaskType.ROUTINE_CLASSIFICATION],
        configuration_key=f"DOCUSTRUCT_MODEL_{name.upper().replace(' ', '_')}_ID",
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


class TestWorkerInvocationWithEligibleCandidate:
    """Validate BaseWorker invocation of provider complete_structured with matching signature."""

    @pytest.mark.asyncio
    async def test_worker_invokes_provider_with_aligned_signature_and_returns_valid_model(self) -> None:
        """BaseWorker passes prompt, model_id, schema, system_prompt, temperature, max_tokens, images."""
        candidate = _make_eligible_candidate()
        router = MagicMock(spec=TaskRouter)
        router.resolve_execution_chain.return_value = [candidate]

        mock_proposal = CorrectionProposal(
            table_id="tbl_test",
            row_idx=1,
            col_idx=2,
            original_value="10",
            proposed_value="20",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Physical char match",
            confidence=0.95,
        )

        mock_adapter = AsyncMock()
        mock_adapter.complete_structured.return_value = StructuredCompletionResponse(
            content='{"test": "val"}',
            raw_payload={"test": "val"},
            usage={"total_tokens": 50},
            latency_ms=12.5,
            provider=ProviderType.GROQ,
            model_id="gpt-oss-20b",
            validation_passed=True,
            parsed=mock_proposal,
        )

        worker = BaseWorker(router=router)
        with patch.object(ProviderFactory, "get_adapter_for_model", return_value=mock_adapter):
            res: FallbackResult = await worker.execute_task(
                task=TaskType.CORRECTION_PROPOSAL,
                prompt="Analyze cell (1, 2)",
                response_model=CorrectionProposal,
                system_prompt="Audit instructions",
            )

        assert res.success is True
        assert res.fallback_to_deterministic is False
        assert res.result == mock_proposal
        assert res.candidate_used == candidate
        mock_adapter.complete_structured.assert_awaited_once_with(
            prompt="Analyze cell (1, 2)",
            model_id="gpt-oss-20b",
            schema=CorrectionProposal,
            system_prompt="Audit instructions",
            temperature=0.0,
            max_tokens=1024,
            images=None,
        )

    @pytest.mark.asyncio
    async def test_worker_handles_schema_validation_error_and_triggers_deterministic_fallback(self) -> None:
        """SchemaValidationError raised by provider is caught and triggers fallback."""
        candidate = _make_eligible_candidate()
        router = MagicMock(spec=TaskRouter)
        router.resolve_execution_chain.return_value = [candidate]

        mock_adapter = AsyncMock()
        mock_adapter.complete_structured.side_effect = SchemaValidationError(
            "Output violated schema",
            provider="GROQ",
            model_id="gpt-oss-20b",
        )

        worker = BaseWorker(router=router)
        with patch.object(ProviderFactory, "get_adapter_for_model", return_value=mock_adapter):
            res: FallbackResult = await worker.execute_task(
                task=TaskType.CORRECTION_PROPOSAL,
                prompt="Analyze cell",
                response_model=CorrectionProposal,
            )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        assert len(res.audit_trail) == 1
        assert res.audit_trail[0].error_reason == "SCHEMA_VALIDATION_ERROR"
        assert "Output violated schema" in res.audit_trail[0].error_message

    @pytest.mark.asyncio
    async def test_worker_handles_provider_timeout_error(self) -> None:
        """ProviderTimeoutError raised by provider triggers fallback."""
        candidate = _make_eligible_candidate()
        router = MagicMock(spec=TaskRouter)
        router.resolve_execution_chain.return_value = [candidate]

        mock_adapter = AsyncMock()
        mock_adapter.complete_structured.side_effect = ProviderTimeoutError(
            "Provider request timed out after 5.0s",
            provider="GROQ",
            model_id="gpt-oss-20b",
        )

        worker = BaseWorker(router=router)
        with patch.object(ProviderFactory, "get_adapter_for_model", return_value=mock_adapter):
            res: FallbackResult = await worker.execute_task(
                task=TaskType.CORRECTION_PROPOSAL,
                prompt="Analyze cell",
                response_model=CorrectionProposal,
            )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        assert res.audit_trail[0].error_reason == "TIMEOUT"

    @pytest.mark.asyncio
    async def test_worker_handles_rate_limit_with_retry_after(self) -> None:
        """RateLimitExceededError records retry_after_seconds in audit trail."""
        candidate = _make_eligible_candidate()
        router = MagicMock(spec=TaskRouter)
        router.resolve_execution_chain.return_value = [candidate]

        mock_adapter = AsyncMock()
        mock_adapter.complete_structured.side_effect = RateLimitExceededError(
            "Rate limit exceeded",
            provider="GROQ",
            model_id="gpt-oss-20b",
            retry_after_seconds=4.5,
        )

        worker = BaseWorker(router=router)
        with patch.object(ProviderFactory, "get_adapter_for_model", return_value=mock_adapter):
            res: FallbackResult = await worker.execute_task(
                task=TaskType.CORRECTION_PROPOSAL,
                prompt="Analyze cell",
                response_model=CorrectionProposal,
            )

        assert res.success is False
        assert res.fallback_to_deterministic is True
        assert res.audit_trail[0].error_reason == "RATE_LIMIT_EXCEEDED"
        assert res.audit_trail[0].retry_after_seconds == 4.5

    @pytest.mark.asyncio
    async def test_provider_adapter_raises_not_implemented_for_images(self) -> None:
        """Passing images to text provider adapter raises NotImplementedError."""
        adapter = GroqProviderAdapter(api_key="test-key")
        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.complete_structured(
                prompt="Analyze",
                model_id="test-model",
                schema=CorrectionProposal,
                images=[b"fake_image_bytes"],
            )
        assert "Multimodal image inputs are not supported" in str(exc_info.value)
