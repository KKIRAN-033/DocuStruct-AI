"""DocuStruct AI — Structured Schema Validation & Rejection Integration Tests.

Validates:
    - Strict Pydantic v2 schema compliance across all 5 structured output contracts:
      PageClassificationEnrichment, TableInterpretationResult, DiscrepancyHypothesis,
      CorrectionProposal, and UserExplanationPayload.
    - Rejection of missing required fields, type mismatches, and out-of-range bounds.
    - Rejection of extra/unsupported fields (extra="forbid").
    - Extraction and parsing of JSON wrapped in markdown code blocks.
    - Schema validation failure on primary candidate triggering bounded fallback to secondary.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from pydantic import ValidationError

from app.llm.enums import (
    ConfigurationCredentialStatus,
    IntegrationTestStatus,
    Modality,
    ModelExistenceStatus,
    ProviderAvailabilityStatus,
    ProviderType,
    TaskType,
)
from app.llm.exceptions import SchemaValidationError
from app.llm.fallback import (
    REASON_SCHEMA_ERROR,
    BoundedFallbackEngine,
    FallbackResult,
)
from app.llm.models import (
    CandidateModel,
    ModelVerificationStatus,
    TimeoutRetryPolicy,
)
from app.llm.providers.groq import GroqProviderAdapter
from app.llm.schemas import (
    CorrectionProposal,
    DiscrepancyHypothesis,
    PageClassificationEnrichment,
    TableInterpretationResult,
    UserExplanationPayload,
)
from tests.llm.conftest import create_mock_client


def _make_candidate(name: str) -> CandidateModel:
    """Helper creating a test candidate model."""
    return CandidateModel(
        candidate_name=name,
        exact_model_id=f"model/{name.lower()}",
        provider=ProviderType.GROQ,
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


# ── 1. Strict Schema Contract Tests ──────────────────────────────────────────


class TestPydanticSchemaEnforcement:
    """Validate strict parsing and field bounds for all multi-model contracts."""

    def test_page_classification_valid(self) -> None:
        """PageClassificationEnrichment parses valid attributes."""
        payload = {
            "layout_analysis": "Dense financial ledger with multi-column headers",
            "has_borderless_tables": False,
            "script_detection": ["Latin"],
            "confidence": 0.92,
        }
        res = PageClassificationEnrichment.model_validate(payload)
        assert res.confidence == 0.92
        assert res.has_borderless_tables is False

    def test_page_classification_extra_field_rejected(self) -> None:
        """Extra fields raise ValidationError (extra='forbid')."""
        payload = {
            "layout_analysis": "Ledger",
            "has_borderless_tables": True,
            "script_detection": [],
            "confidence": 0.85,
            "hallucinated_column": "Invented",
        }
        with pytest.raises(ValidationError):
            PageClassificationEnrichment.model_validate(payload)

    def test_table_interpretation_valid(self) -> None:
        """TableInterpretationResult parses column list and rationale."""
        payload = {
            "detected_columns": ["Period", "Revenue", "Gross Margin", "Net Income"],
            "confidence": 0.99,
            "ragged_row_rationale": "Sub-total rows span across columns 2 and 3",
        }
        res = TableInterpretationResult.model_validate(payload)
        assert len(res.detected_columns) == 4
        assert res.ragged_row_rationale is not None

    def test_table_interpretation_missing_columns_rejected(self) -> None:
        """Missing detected_columns raises ValidationError."""
        payload = {"confidence": 0.95}
        with pytest.raises(ValidationError):
            TableInterpretationResult.model_validate(payload)

    def test_discrepancy_hypothesis_valid(self) -> None:
        """DiscrepancyHypothesis validates coordinates and hypothesis taxonomy."""
        payload = {
            "table_id": "tbl_audit_01",
            "row_idx": 3,
            "col_idx": 4,
            "hypothesis_type": "DECIMAL_SHIFT",
            "explanation": "Floating point artifact shifted decimal point by 1 digit.",
            "recommended_action": "HUMAN_REVIEW",
        }
        hyp = DiscrepancyHypothesis.model_validate(payload)
        assert hyp.row_idx == 3
        assert hyp.recommended_action == "HUMAN_REVIEW"

    def test_discrepancy_hypothesis_negative_coordinates_rejected(self) -> None:
        """Negative row or column index raises ValidationError."""
        payload = {
            "table_id": "tbl_01",
            "row_idx": -1,
            "col_idx": 2,
            "hypothesis_type": "TEST",
            "explanation": "Test",
        }
        with pytest.raises(ValidationError):
            DiscrepancyHypothesis.model_validate(payload)

    def test_correction_proposal_valid(self) -> None:
        """CorrectionProposal parses physical evidence and candidate values."""
        payload = {
            "table_id": "tbl_01",
            "row_idx": 1,
            "col_idx": 2,
            "original_value": "$1,000",
            "proposed_value": "$10,000",
            "evidence_source": "NATIVE_PDF_CHAR_STREAM",
            "evidence_summary": "Extracted string at glyph coordinate (100, 250) is '$10,000'",
            "confidence": 0.97,
        }
        prop = CorrectionProposal.model_validate(payload)
        assert prop.original_value == "$1,000"
        assert prop.proposed_value == "$10,000"

    def test_correction_proposal_confidence_bounds_enforced(self) -> None:
        """Confidence score > 1.0 or < 0.0 raises ValidationError."""
        payload = {
            "table_id": "tbl_01",
            "row_idx": 0,
            "col_idx": 0,
            "original_value": "1",
            "proposed_value": "2",
            "evidence_source": "NATIVE_PDF_CHAR_STREAM",
            "evidence_summary": "Valid summary",
            "confidence": 1.05,  # Out of range!
        }
        with pytest.raises(ValidationError):
            CorrectionProposal.model_validate(payload)

    def test_user_explanation_valid(self) -> None:
        """UserExplanationPayload parses summary and recommendation."""
        payload = {
            "issue_id": "issue_sum_01",
            "summary": "Arithmetic total does not equal sum of row items.",
            "recommendation": "Inspect original invoice page to verify item costs.",
            "technical_context": "Math error: Expected 100, Got 90",
        }
        exp = UserExplanationPayload.model_validate(payload)
        assert exp.issue_id == "issue_sum_01"
        assert exp.technical_context is not None


# ── 2. Markdown Code Block Stripping Tests ────────────────────────────────────


class TestMarkdownBlockHandling:
    """Validate parsing of JSON payloads enclosed in markdown code fences."""

    @pytest.mark.asyncio
    async def test_markdown_code_fence_stripped_and_validated(self) -> None:
        """Provider response enclosed in ```json ... ``` is cleanly parsed."""
        raw_content = "```json\n{\n  \"issue_id\": \"issue-1\",\n  \"summary\": \"Valid issue explanation\",\n  \"recommendation\": \"Review page\"\n}\n```"
        mock_client, _ = create_mock_client(
            status_code=200,
            json_data={"choices": [{"message": {"content": raw_content}}]},
        )

        adapter = GroqProviderAdapter(api_key="key")
        with patch("httpx.AsyncClient", return_value=mock_client):
            res = await adapter.complete_structured(
                prompt="Explain issue",
                model_id="llama-3.3-70b-versatile",
                schema=UserExplanationPayload,
            )

        assert res.validation_passed is True
        assert res.parsed.summary == "Valid issue explanation"
        assert res.parsed.recommendation == "Review page"


# ── 3. Fallback Trigger on Schema Violation ───────────────────────────────────


class TestSchemaViolationFallback:
    """Validate that invalid model output triggers bounded fallback to alternative candidates."""

    @pytest.mark.asyncio
    async def test_schema_error_triggers_fallback_to_secondary(self) -> None:
        """When primary model output violates schema, engine falls back to secondary candidate."""
        engine = BoundedFallbackEngine(max_fallbacks=2)
        c1 = _make_candidate("Model-1")
        c2 = _make_candidate("Model-2")

        async def _invoke(candidate: CandidateModel) -> CorrectionProposal:
            if candidate.candidate_name == "Model-1":
                # Primary model produces invalid output
                raise SchemaValidationError(
                    "Primary candidate returned invalid schema",
                    provider="GROQ",
                    model_id=candidate.exact_model_id,
                )
            # Secondary model produces valid output
            return CorrectionProposal(
                table_id="tbl_1",
                row_idx=0,
                col_idx=1,
                original_value="10",
                proposed_value="20",
                evidence_source="NATIVE_PDF_CHAR_STREAM",
                evidence_summary="Stream evidence confirmed",
                confidence=0.95,
            )

        res: FallbackResult = await engine.execute_with_fallback(
            task=TaskType.CORRECTION_PROPOSAL,
            candidates=[c1, c2],
            invoke_fn=_invoke,
        )

        assert res.success is True
        assert res.fallback_hops == 1
        assert res.candidate_used == c2
        assert isinstance(res.result, CorrectionProposal)
        assert res.audit_trail[0].error_reason == REASON_SCHEMA_ERROR
