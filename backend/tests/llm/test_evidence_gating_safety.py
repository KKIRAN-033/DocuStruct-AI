"""DocuStruct AI — Evidence-Gating Safety & Deterministic Supremacy Tests.

Validates:
    - cell.raw_value is strictly immutable across all candidate workflows.
    - Prohibition of auto-balancing totals (DECISION-007, DECISION-011, Section 15).
    - Rejection of unapproved evidence sources (LLM_GUESS, HEURISTIC, WEB_SEARCH).
    - Acceptance of permitted deterministic evidence (NATIVE_PDF_CHAR_STREAM, etc.).
    - Immediate deterministic re-validation via evaluate_table_arithmetic_consistency.
    - Authoritative quality gate supremacy: AI cannot bypass security checks or execution states.
    - Adversarial output handling (formula injection, non-numeric values, malformed data).
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from app.extraction.normalizer import normalize_cell
from app.extraction.table_reconstructor import PERMITTED_EVIDENCE_SOURCES
from app.llm.schemas import CorrectionProposal
from app.llm.workers.correction_worker import CorrectionWorker
from app.models.domain import CanonicalTable, CellRecord, CorrectionRecord
from app.models.state import (
    CellQualityStatus,
    DataType,
    JobExecutionState,
    ValidationOutcome,
    VerificationStatus,
)
from app.verification.quality_gate import (
    REASON_SOURCE_ARITHMETIC_DISCREPANCY,
    evaluate_table_arithmetic_consistency,
)


def _build_test_cell(
    raw: str,
    accepted: str,
    row: int,
    col: int,
    table_id: str = "t1",
    numeric: Decimal | None = None,
    dtype: DataType = DataType.DECIMAL,
    status: CellQualityStatus = CellQualityStatus.CORROBORATED,
) -> CellRecord:
    """Helper building a single test CellRecord."""
    return CellRecord(
        table_id=table_id,
        row_idx=row,
        col_idx=col,
        source_page=1,
        extraction_method="stream",
        raw_value=raw,
        accepted_value=accepted,
        numeric_decimal=numeric or (Decimal(accepted.replace(",", "")) if accepted.replace(".", "").replace(",", "").isdigit() else None),
        data_type=dtype,
        quality_status=status,
    )


# ── 1. Raw Value Immutability Tests ──────────────────────────────────────────


class TestRawValueImmutability:
    """Validate that cell.raw_value is strictly immutable under all conditions."""

    def test_raw_value_preserved_on_valid_evidence_correction(self) -> None:
        """Raw value is never overwritten even when a correction is fully accepted."""
        worker = CorrectionWorker()
        cell = _build_test_cell(raw="1O.50", accepted="1O.50", row=1, col=1)

        prop = CorrectionProposal(
            table_id=cell.table_id,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_value=cell.raw_value,
            proposed_value="10.50",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Digit '0' found at glyph stream offset 12",
            confidence=0.99,
        )

        updated_cell, record = worker.apply_proposal(cell, prop, is_total_or_sum_cell=False)
        assert updated_cell.raw_value == "1O.50"
        assert updated_cell.accepted_value == "10.50"
        assert record.decision == "CORRECTION_ACCEPTED"

    def test_raw_value_preserved_on_unapproved_evidence(self) -> None:
        """Raw value is preserved when proposal is backed by unapproved evidence."""
        worker = CorrectionWorker()
        cell = _build_test_cell(raw="500", accepted="500", row=2, col=1)

        prop = CorrectionProposal(
            table_id=cell.table_id,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_value=cell.raw_value,
            proposed_value="550",
            evidence_source="LLM_GUESS",
            evidence_summary="Model hallucination",
            confidence=0.5,
        )

        updated_cell, record = worker.apply_proposal(cell, prop, is_total_or_sum_cell=False)
        assert updated_cell.raw_value == "500"
        assert updated_cell.accepted_value == "500"
        assert updated_cell.inferred_candidate_value == "550"
        assert record.inferred_candidate_only is True

    def test_raw_value_preserved_on_auto_balance_attempt(self) -> None:
        """Raw value is preserved when proposal attempts to auto-balance a sum/total cell."""
        worker = CorrectionWorker()
        cell = _build_test_cell(raw="350", accepted="350", row=3, col=1)

        prop = CorrectionProposal(
            table_id=cell.table_id,
            row_idx=cell.row_idx,
            col_idx=cell.col_idx,
            original_value=cell.raw_value,
            proposed_value="300",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Sum balance adjustment",
            confidence=0.99,
        )

        updated_cell, record = worker.apply_proposal(cell, prop, is_total_or_sum_cell=True)
        assert updated_cell.raw_value == "350"
        assert updated_cell.accepted_value == "350"
        assert updated_cell.inferred_candidate_value == "300"
        assert "REJECTED_AUTO_BALANCE" in record.decision


# ── 2. Prohibition of Auto-Balancing Arithmetic Totals ────────────────────────


class TestAutoBalancingProhibition:
    """Validate DECISION-007 and DECISION-011: math discrepancies preserve raw printed totals."""

    def test_arithmetic_discrepancy_table_rejects_llm_auto_balance(self) -> None:
        """Table with 100 + 200 = 350 rejects LLM proposal attempting to change 350 to 300."""
        # Row 0: Header
        # Row 1: Item A = 100.00
        # Row 2: Item B = 200.00
        # Row 3: Total = 350.00 (Printed discrepancy in source PDF)
        h_row = [
            _build_test_cell("Description", "Description", 0, 0, dtype=DataType.STRING),
            _build_test_cell("Amount", "Amount", 0, 1, dtype=DataType.STRING),
        ]
        r1 = [
            _build_test_cell("Item A", "Item A", 1, 0, dtype=DataType.STRING),
            _build_test_cell("100.00", "100.00", 1, 1, numeric=Decimal("100.00")),
        ]
        r2 = [
            _build_test_cell("Item B", "Item B", 2, 0, dtype=DataType.STRING),
            _build_test_cell("200.00", "200.00", 2, 1, numeric=Decimal("200.00")),
        ]
        total_cell = _build_test_cell("350.00", "350.00", 3, 1, numeric=Decimal("350.00"))
        r3 = [
            _build_test_cell("Total", "Total", 3, 0, dtype=DataType.STRING),
            total_cell,
        ]

        table = CanonicalTable(
            table_id="tbl_discrepancy",
            source_pages=[1],
            original_headers=["Description", "Amount"],
            normalized_headers=["Description", "Amount"],
            header_row_count=1,
            rows=[h_row, r1, r2, r3],
        )

        # 1. Deterministic baseline evaluation flags discrepancy
        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.FAILED_VALIDATION
        assert any(i.issue_code == REASON_SOURCE_ARITHMETIC_DISCREPANCY for i in issues)

        # 2. LLM attempts to "fix" the math discrepancy by forcing 350.00 -> 300.00
        worker = CorrectionWorker()
        proposal = CorrectionProposal(
            table_id=table.table_id,
            row_idx=3,
            col_idx=1,
            original_value="350.00",
            proposed_value="300.00",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Arithmetic calculation 100 + 200 = 300",
            confidence=0.98,
        )

        updated_cell, record = worker.apply_proposal(
            total_cell,
            proposal,
            is_total_or_sum_cell=True,  # Row 3 is a 'Total' row
        )

        # 3. Assert accepted_value is UNCHANGED and discrepancy remains reported
        assert updated_cell.accepted_value == "350.00"
        assert updated_cell.raw_value == "350.00"
        assert updated_cell.inferred_candidate_value == "300.00"

        # Update table with candidate and re-evaluate
        table.rows[3][1] = updated_cell
        re_outcome, re_issues = evaluate_table_arithmetic_consistency(table)
        assert re_outcome == ValidationOutcome.FAILED_VALIDATION
        assert any(i.issue_code == REASON_SOURCE_ARITHMETIC_DISCREPANCY for i in re_issues)


# ── 3. Permitted vs Unapproved Evidence Sources ──────────────────────────────


class TestEvidenceSourceEnforcement:
    """Validate PERMITTED_EVIDENCE_SOURCES allowlist."""

    def test_permitted_sources_set_contents(self) -> None:
        """PERMITTED_EVIDENCE_SOURCES must contain exactly the 3 approved deterministic sources."""
        assert PERMITTED_EVIDENCE_SOURCES == frozenset({
            "NATIVE_PDF_CHAR_STREAM",
            "INDEPENDENT_WORD_COORDINATES",
            "VECTOR_GRID_GEOMETRY",
        })

    def test_unapproved_sources_rejected_across_multiple_heuristics(self) -> None:
        """Sources like 'LLM_GUESS', 'WEB_SEARCH', 'HEURISTIC' are unconditionally rejected."""
        worker = CorrectionWorker()
        unapproved = ["LLM_GUESS", "WEB_SEARCH", "PROMPT_HEURISTIC", "USER_ESTIMATE"]

        for source in unapproved:
            cell = _build_test_cell("100", "100", 1, 1)
            prop = CorrectionProposal(
                table_id="tbl_1",
                row_idx=1,
                col_idx=1,
                original_value="100",
                proposed_value="150",
                evidence_source=source,
                evidence_summary="Unverified external data",
                confidence=0.9,
            )
            updated, record = worker.apply_proposal(cell, prop)
            assert updated.accepted_value == "100"
            assert updated.inferred_candidate_value == "150"
            assert record.inferred_candidate_only is True
            assert record.deterministic_check_passed is False


# ── 4. Deterministic Re-Validation ───────────────────────────────────────────


class TestDeterministicReValidation:
    """Validate that accepting an evidence-backed edit immediately triggers re-validation."""

    def test_legitimate_correction_passes_arithmetic_revalidation(self) -> None:
        """When an OCR error ('1O0' instead of '100') is corrected with valid evidence, re-validation passes."""
        # Row 0: Header
        # Row 1: Item 1 = 1O0 (corrupted OCR glyph)
        # Row 2: Item 2 = 200.00
        # Row 3: Total = 300.00
        h_row = [
            _build_test_cell("Desc", "Desc", 0, 0, dtype=DataType.STRING),
            _build_test_cell("Amt", "Amt", 0, 1, dtype=DataType.STRING),
        ]
        bad_cell = _build_test_cell("1O0", "1O0", 1, 1, dtype=DataType.STRING)  # Text due to 'O'
        r1 = [_build_test_cell("Item 1", "Item 1", 1, 0, dtype=DataType.STRING), bad_cell]
        r2 = [
            _build_test_cell("Item 2", "Item 2", 2, 0, dtype=DataType.STRING),
            _build_test_cell("200.00", "200.00", 2, 1, numeric=Decimal("200.00")),
        ]
        r3 = [
            _build_test_cell("Total", "Total", 3, 0, dtype=DataType.STRING),
            _build_test_cell("300.00", "300.00", 3, 1, numeric=Decimal("300.00")),
        ]

        table = CanonicalTable(
            table_id="tbl_reval",
            source_pages=[1],
            original_headers=["Desc", "Amt"],
            normalized_headers=["Desc", "Amt"],
            header_row_count=1,
            rows=[h_row, r1, r2, r3],
        )

        # Baseline evaluation fails because Item 1 is non-numeric
        outcome_before, _ = evaluate_table_arithmetic_consistency(table)
        assert outcome_before == ValidationOutcome.FAILED_VALIDATION

        # Apply correction backed by native PDF character stream
        worker = CorrectionWorker()
        proposal = CorrectionProposal(
            table_id="tbl_reval",
            row_idx=1,
            col_idx=1,
            original_value="1O0",
            proposed_value="100.00",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Digit glyph 0 found at char coordinate (50, 100)",
            confidence=0.99,
        )

        corrected_cell, record = worker.apply_proposal(bad_cell, proposal, is_total_or_sum_cell=False)
        assert corrected_cell.accepted_value == "100.00"
        assert corrected_cell.numeric_decimal == Decimal("100.00")
        assert corrected_cell.raw_value == "1O0"  # Raw value is preserved!

        # Inject into table and re-validate
        table.rows[1][1] = corrected_cell
        outcome_after, issues_after = evaluate_table_arithmetic_consistency(table)
        # Re-validation passes: 100 + 200 = 300!
        assert outcome_after == ValidationOutcome.PASSED
        assert len(issues_after) == 0


# ── 5. Adversarial and Formula Injection Safety ──────────────────────────────


class TestAdversarialModelOutputSafety:
    """Validate system defense against adversarial or malformed candidate outputs."""

    def test_formula_injection_proposal_is_neutralized(self) -> None:
        """A proposal containing Excel formula injection trigger ('=SUM(...)') flags formula risk."""
        norm = normalize_cell("=SUM(A1:A5)")
        # Normalizer detects formula risk
        assert norm["formula_risk_detected"] is True

    def test_script_tag_in_proposal_does_not_break_domain_models(self) -> None:
        """XSS/HTML injected proposal is safely treated as literal text."""
        worker = CorrectionWorker()
        cell = _build_test_cell("normal", "normal", 1, 1, dtype=DataType.STRING)

        proposal = CorrectionProposal(
            table_id="tbl_1",
            row_idx=1,
            col_idx=1,
            original_value="normal",
            proposed_value="<script>alert('xss')</script>",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Literal text from PDF",
            confidence=0.9,
        )

        updated_cell, record = worker.apply_proposal(cell, proposal)
        # Accepted as literal string without code execution
        assert updated_cell.accepted_value == "<script>alert('xss')</script>"
        assert updated_cell.raw_value == "normal"
