"""DocuStruct AI — Unit Tests: Table Arithmetic Consistency & Document Quality Gate

Tests exact Decimal arithmetic verification, source discrepancy reporting and value preservation,
ambiguous calculation scope handling, conservative document verification precedence, reason code assignment,
and verbatim disclaimer attachment in accordance with MASTER_DIRECTIVE.md Sections 16, 17, and 20.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from app.extraction.normalizer import normalize_cell
from app.models.domain import (
    BoundingBox,
    CanonicalTable,
    CellRecord,
    CorrectionRecord,
    DocumentEvaluationReport,
    PageExtractionResult,
    PageProfile,
    StitchAuditEvent,
    ValidationIssue,
)
from app.models.state import (
    CellQualityStatus,
    DataType,
    JobExecutionState,
    PageProcessingStatus,
    PageType,
    StitchDecision,
    TablePresenceStatus,
    ValidationOutcome,
    VerificationStatus,
)
from app.verification.quality_gate import (
    MANDATORY_VERBATIM_DISCLAIMER,
    REASON_ARITHMETIC_SCOPE_AMBIGUOUS,
    REASON_DEFERRED_REGIONS_REMAIN,
    REASON_EXECUTION_FAILED,
    REASON_NO_TABLES_FOUND,
    REASON_OCR_REQUIRED_FOR_SCANNED,
    REASON_SOURCE_ARITHMETIC_DISCREPANCY,
    REASON_STITCH_REVIEW_REQUIRED,
    REASON_STRUCTURAL_CHECKS_FAILED,
    evaluate_document_quality,
    evaluate_document_verification_status,
    evaluate_table_arithmetic_consistency,
    identify_numeric_columns,
    identify_summary_rows,
)


# ── Helper Functions ────────────────────────────────────────────────────────


def _make_cell(
    table_id: str,
    row_idx: int,
    col_idx: int,
    page_num: int,
    text: str,
) -> CellRecord:
    """Helper to create a validated normalized CellRecord."""
    norm = normalize_cell(text)
    return CellRecord(
        table_id=table_id,
        row_idx=row_idx,
        col_idx=col_idx,
        source_page=page_num,
        extraction_method="LINE_BASED_RULING",
        raw_value=norm["raw_value"],
        normalized_value=norm["normalized_value"],
        accepted_value=norm["accepted_value"],
        numeric_decimal=norm["numeric_decimal"],
        data_type=norm["data_type"],
        quality_status=CellQualityStatus.EXTRACTED_AS_IS,
        formula_risk_detected=norm["formula_risk_detected"],
    )


def _make_table(
    table_id: str,
    headers: list[str],
    rows_data: list[list[str]],
    page_num: int = 1,
    structural_passed: bool = True,
) -> CanonicalTable:
    """Helper to construct a CanonicalTable with normalized cells."""
    table_rows: list[list[CellRecord]] = []

    # Header row (index 0)
    header_cells = [
        _make_cell(table_id, 0, c_idx, page_num, h_text)
        for c_idx, h_text in enumerate(headers)
    ]
    table_rows.append(header_cells)

    # Body rows (index 1+)
    for r_idx, row_strings in enumerate(rows_data, start=1):
        row_cells = [
            _make_cell(table_id, r_idx, c_idx, page_num, val)
            for c_idx, val in enumerate(row_strings)
        ]
        table_rows.append(row_cells)

    return CanonicalTable(
        table_id=table_id,
        source_pages=[page_num],
        original_headers=headers,
        normalized_headers=[h.lower().strip() for h in headers],
        header_row_count=1,
        rows=table_rows,
        extraction_method="LINE_BASED_RULING",
        structural_checks_passed=structural_passed,
    )


def _make_report(
    execution_state: JobExecutionState = JobExecutionState.COMPLETED,
    verification_status: VerificationStatus = VerificationStatus.REVIEW_REQUIRED,
    canonical_tables: list[CanonicalTable] | None = None,
    page_profiles: list[PageProfile] | None = None,
    stitch_events: list[StitchAuditEvent] | None = None,
    validation_issues: list[ValidationIssue] | None = None,
    correction_records: list[CorrectionRecord] | None = None,
) -> DocumentEvaluationReport:
    """Helper to create a populated DocumentEvaluationReport."""
    return DocumentEvaluationReport(
        job_id="test-job-uuid",
        source_filename="test_doc.pdf",
        execution_state=execution_state,
        verification_status=verification_status,
        status_reason_codes=[],
        limitation_disclaimers=[],
        page_profiles=page_profiles or [],
        page_results=[],
        canonical_tables=canonical_tables or [],
        stitch_events=stitch_events or [],
        validation_issues=validation_issues or [],
        correction_records=correction_records or [],
    )


# ── Test Suite 1: Table Arithmetic Consistency ─────────────────────────────


class TestTableArithmeticConsistency:
    """Tests for evaluate_table_arithmetic_consistency."""

    def test_correct_total_row_passed(self) -> None:
        """Table with matching total row yields PASSED and 0 issues."""
        table = _make_table(
            "tbl-1",
            ["Item", "Amount"],
            [
                ["Alpha", "100.00"],
                ["Beta", "200.00"],
                ["Total", "300.00"],
            ],
        )

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.PASSED
        assert len(issues) == 0
        assert table.math_validation_outcome == ValidationOutcome.PASSED

    def test_arithmetic_discrepancy_preserves_values_and_flags_anomaly(self) -> None:
        """Arithmetic discrepancy (100+200=350) yields FAILED_VALIDATION, preserves printed values,

        flags cell as ANOMALY_FLAGGED, and strictly refuses to auto-balance.
        """
        table = _make_table(
            "tbl-disc",
            ["Item", "Amount"],
            [
                ["Alpha", "100.00"],
                ["Beta", "200.00"],
                ["Total", "350.00"],
            ],
        )

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.FAILED_VALIDATION
        assert len(issues) == 1

        issue = issues[0]
        assert issue.issue_code == REASON_SOURCE_ARITHMETIC_DISCREPANCY
        assert issue.severity == "ERROR"
        assert issue.expected_value == "300.00"
        assert issue.actual_value == "350.00"
        assert issue.row_idx == 3
        assert issue.col_idx == 1

        # Check total cell preservation
        total_cell = table.rows[3][1]
        assert total_cell.raw_value == "350.00"
        assert total_cell.accepted_value == "350.00"
        assert total_cell.quality_status == CellQualityStatus.ANOMALY_FLAGGED

    def test_negative_numbers_sum_accurately(self) -> None:
        """Negative and accounting values are summed accurately using exact Decimal."""
        table = _make_table(
            "tbl-neg",
            ["Description", "Balance"],
            [
                ["Deposit", "100.00"],
                ["Fee", "(40.00)"],
                ["Total", "60.00"],
            ],
        )

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.PASSED
        assert len(issues) == 0

    def test_subtotals_and_grand_total_evaluation(self) -> None:
        """Subtotals sum preceding section rows and Grand Total sums subtotals."""
        table = _make_table(
            "tbl-multi-summary",
            ["Category", "Amount"],
            [
                ["Item A1", "50.00"],
                ["Item A2", "50.00"],
                ["Subtotal A", "100.00"],
                ["Item B1", "75.00"],
                ["Item B2", "25.00"],
                ["Subtotal B", "100.00"],
                ["Grand Total", "200.00"],
            ],
        )

        summary_rows = identify_summary_rows(table)
        assert len(summary_rows) == 3
        assert summary_rows[0] == (3, "SUBTOTAL")
        assert summary_rows[1] == (6, "SUBTOTAL")
        assert summary_rows[2] == (7, "GRAND_TOTAL")

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.PASSED
        assert len(issues) == 0

    def test_no_total_row_yields_not_applicable(self) -> None:
        """Table with only regular body data yields NOT_APPLICABLE and 0 issues."""
        table = _make_table(
            "tbl-no-total",
            ["Product", "Price"],
            [
                ["Widget A", "10.00"],
                ["Widget B", "20.00"],
            ],
        )

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.NOT_APPLICABLE
        assert len(issues) == 0

    def test_ambiguous_calculation_scope(self) -> None:
        """Summary row with 0 preceding body rows yields FAILED_VALIDATION and ARITHMETIC_SCOPE_AMBIGUOUS."""
        table = _make_table(
            "tbl-ambig",
            ["Category", "Amount"],
            [
                ["Total", "100.00"],  # Immediately after header
            ],
        )

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.FAILED_VALIDATION
        assert len(issues) == 1
        assert issues[0].issue_code == REASON_ARITHMETIC_SCOPE_AMBIGUOUS
        assert issues[0].severity == "WARNING"

    def test_no_false_corroboration_of_participating_cells(self) -> None:
        """Participating body cells are NEVER marked CORROBORATED solely because sum matches."""
        table = _make_table(
            "tbl-no-false-corrob",
            ["Item", "Amount"],
            [
                ["Alpha", "100.00"],
                ["Beta", "200.00"],
                ["Total", "300.00"],
            ],
        )

        outcome, _ = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.PASSED

        # Body cells must remain EXTRACTED_AS_IS, not CORROBORATED
        assert table.rows[1][1].quality_status == CellQualityStatus.EXTRACTED_AS_IS
        assert table.rows[2][1].quality_status == CellQualityStatus.EXTRACTED_AS_IS

    def test_prose_label_rejected_as_summary(self) -> None:
        """Sentences containing 'total' in narrative rows are rejected from summary row detection."""
        table = _make_table(
            "tbl-prose",
            ["Clause", "Ref"],
            [
                ["Total liability shall not exceed statutory limits in any circumstance", "10.00"],
            ],
        )

        summary_rows = identify_summary_rows(table)
        assert len(summary_rows) == 0

        outcome, issues = evaluate_table_arithmetic_consistency(table)
        assert outcome == ValidationOutcome.NOT_APPLICABLE


# ── Test Suite 2: Document Quality Gate ─────────────────────────────────────


class TestDocumentQualityGate:
    """Tests for evaluate_document_verification_status and evaluate_document_quality."""

    def test_fatal_execution_state_yields_failed(self) -> None:
        """Execution failure takes absolute precedence, yielding FAILED and EXECUTION_FAILED."""
        report = _make_report(execution_state=JobExecutionState.FAILED)
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.FAILED
        assert reasons == [REASON_EXECUTION_FAILED]

    def test_zero_table_digital_document_yields_failed_no_tables_found(self) -> None:
        """Fully inspected digital document with 0 tables and CONFIRMED_ABSENT yields FAILED and NO_TABLES_FOUND."""
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_ABSENT,
            printable_char_count=500,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=0,
            deferred_regions_count=0,
        )
        report = _make_report(page_profiles=[page_prof])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.FAILED
        assert reasons == [REASON_NO_TABLES_FOUND]

    def test_scanned_content_yields_review_required_ocr_needed(self) -> None:
        """Scanned content yields REVIEW_REQUIRED and OCR_REQUIRED_FOR_SCANNED_CONTENT, never CONFIRMED_ABSENT."""
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.SCANNED,
            processing_status=PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR,
            table_presence=TablePresenceStatus.UNKNOWN_PENDING_OCR,
            printable_char_count=0,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.9,
            vector_line_count=0,
            deferred_regions_count=0,
        )
        report = _make_report(page_profiles=[page_prof])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.REVIEW_REQUIRED
        assert reasons == [REASON_OCR_REQUIRED_FOR_SCANNED]

    def test_hybrid_document_with_deferred_regions(self) -> None:
        """Hybrid page with unextracted deferred regions yields REVIEW_REQUIRED."""
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.HYBRID,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=300,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.3,
            vector_line_count=5,
            deferred_regions_count=2,
        )
        report = _make_report(page_profiles=[page_prof])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.REVIEW_REQUIRED
        assert reasons == [REASON_DEFERRED_REGIONS_REMAIN]

    def test_unresolved_stitch_review_yields_review_required(self) -> None:
        """Unresolved multipage table stitch decision yields REVIEW_REQUIRED and STITCH_REVIEW_REQUIRED."""
        stitch_event = StitchAuditEvent(
            upper_table_id="tbl-1",
            lower_table_id="tbl-2",
            upper_page=1,
            lower_page=2,
            decision=StitchDecision.STITCH_REVIEW_REQUIRED,
            header_similarity_score=0.70,
            col_overlap_ratio=0.72,
            type_compatibility_ratio=0.80,
            repeated_header_rows_stripped=0,
            reasons=["Borderline score"],
        )
        report = _make_report(stitch_events=[stitch_event])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.REVIEW_REQUIRED
        assert reasons == [REASON_STITCH_REVIEW_REQUIRED]

    def test_arithmetic_discrepancy_in_document_yields_review_required(self) -> None:
        """Arithmetic discrepancy on any table escalates document to REVIEW_REQUIRED."""
        table = _make_table(
            "tbl-disc",
            ["Item", "Amount"],
            [
                ["Alpha", "100.00"],
                ["Beta", "200.00"],
                ["Total", "350.00"],
            ],
        )
        table.math_validation_outcome = ValidationOutcome.FAILED_VALIDATION

        report = _make_report(canonical_tables=[table])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.REVIEW_REQUIRED
        assert REASON_SOURCE_ARITHMETIC_DISCREPANCY in reasons

    def test_structural_checks_failed_yields_review_required(self) -> None:
        """Table failing structural integrity checks causes document REVIEW_REQUIRED."""
        table = _make_table(
            "tbl-fail",
            ["Item", "Amount"],
            [["Alpha", "100.00"]],
            structural_passed=False,
        )
        report = _make_report(canonical_tables=[table])
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.REVIEW_REQUIRED
        assert reasons == [REASON_STRUCTURAL_CHECKS_FAILED]

    def test_clean_document_no_math_checks_yields_verified_with_warnings(self) -> None:
        """Clean document where arithmetic validation was NOT_APPLICABLE yields VERIFIED_WITH_WARNINGS."""
        table = _make_table(
            "tbl-nomath",
            ["Name", "Role"],
            [["Alice", "Engineer"], ["Bob", "Designer"]],
            structural_passed=True,
        )
        table.math_validation_outcome = ValidationOutcome.NOT_APPLICABLE

        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=500,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=4,
            deferred_regions_count=0,
        )
        report = _make_report(
            page_profiles=[page_prof],
            canonical_tables=[table],
        )
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.VERIFIED_WITH_WARNINGS
        assert len(reasons) == 0

    def test_audited_corrections_yields_verified_with_warnings(self) -> None:
        """Clean document with audited corrections applied yields VERIFIED_WITH_WARNINGS."""
        table = _make_table(
            "tbl-correc",
            ["Item", "Amount"],
            [["Alpha", "100.00"], ["Beta", "200.00"], ["Total", "300.00"]],
            structural_passed=True,
        )
        table.math_validation_outcome = ValidationOutcome.PASSED

        correction = CorrectionRecord(
            audit_id="corr-1",
            table_id="tbl-correc",
            source_page=1,
            row_idx=1,
            col_idx=1,
            original_raw_value="1OO.OO",
            proposed_value="100.00",
            accepted_value="100.00",
            inferred_candidate_only=False,
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Extracted ASCII zero from glyph map",
            deterministic_check_passed=True,
            decision="ACCEPTED",
            resulting_cell_status=CellQualityStatus.CORRECTED_WITH_EVIDENCE,
        )
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=500,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=4,
            deferred_regions_count=0,
        )
        report = _make_report(
            page_profiles=[page_prof],
            canonical_tables=[table],
            correction_records=[correction],
        )
        status, _ = evaluate_document_verification_status(report)
        assert status == VerificationStatus.VERIFIED_WITH_WARNINGS

    def test_fully_verified_document(self) -> None:
        """Document with clean extraction, PASSED math, and no warnings yields VERIFIED."""
        table = _make_table(
            "tbl-verif",
            ["Item", "Amount"],
            [["Alpha", "100.00"], ["Beta", "200.00"], ["Total", "300.00"]],
            structural_passed=True,
        )
        table.math_validation_outcome = ValidationOutcome.PASSED

        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=500,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=4,
            deferred_regions_count=0,
        )
        report = _make_report(
            page_profiles=[page_prof],
            canonical_tables=[table],
        )
        status, reasons = evaluate_document_verification_status(report)
        assert status == VerificationStatus.VERIFIED
        assert len(reasons) == 0

    def test_mandatory_verbatim_disclaimer_attached_verbatim(self) -> None:
        """evaluate_document_quality attaches the exact verbatim disclaimer."""
        table = _make_table(
            "tbl-verif",
            ["Item", "Amount"],
            [["Alpha", "100.00"], ["Beta", "200.00"], ["Total", "300.00"]],
            structural_passed=True,
        )
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=500,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=4,
            deferred_regions_count=0,
        )
        report = _make_report(
            page_profiles=[page_prof],
            canonical_tables=[table],
        )

        evaluated_report = evaluate_document_quality(report)
        assert evaluated_report.verification_status == VerificationStatus.VERIFIED
        assert len(evaluated_report.limitation_disclaimers) >= 1
        assert MANDATORY_VERBATIM_DISCLAIMER in evaluated_report.limitation_disclaimers

        # Check exact string match
        expected_text = (
            "Structural integrity and internal arithmetic consistency were verified. "
            "This does not independently prove every source cell is correct and cannot "
            "rule out offsetting cell errors or errors in non-numeric text."
        )
        assert MANDATORY_VERBATIM_DISCLAIMER == expected_text


# ── Test Suite 3: Four Clarifications Explicit Contracts ───────────────────


class TestFourClarificationsExplicitContracts:
    """Explicit tests verifying the four final specification clarifications."""

    def test_clarification_1_math_consistency_distinct_from_cell_corroboration(self) -> None:
        """Clarification 1: Matching totals do not corroborate individual cells; VERIFIED requires all conditions."""
        table = _make_table(
            "tbl-clarif1",
            ["Item", "Amount"],
            [
                ["Service A", "150.00"],
                ["Service B", "250.00"],
                ["Total", "400.00"],
            ],
        )

        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=300,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=4,
            deferred_regions_count=0,
        )
        report = _make_report(page_profiles=[page_prof], canonical_tables=[table])
        evaluated = evaluate_document_quality(report)

        # 1. Arithmetic evaluation ran and PASSED on the canonical table
        assert evaluated.canonical_tables[0].math_validation_outcome == ValidationOutcome.PASSED
        assert len(evaluated.validation_issues) == 0

        # 2. Body cells must NOT be marked CORROBORATED solely because sum matches
        for row in evaluated.canonical_tables[0].rows[1:3]:
            for cell in row:
                assert cell.quality_status == CellQualityStatus.EXTRACTED_AS_IS

        # 3. All required quality-gate conditions for VERIFIED are verified
        assert evaluated.execution_state == JobExecutionState.COMPLETED
        assert len(evaluated.page_profiles) == 1
        assert not any(p.page_type == PageType.SCANNED for p in evaluated.page_profiles)
        assert sum(p.deferred_regions_count for p in evaluated.page_profiles) == 0
        assert evaluated.canonical_tables[0].structural_checks_passed is True
        assert len(evaluated.correction_records) == 0
        assert len(evaluated.stitch_events) == 0
        assert evaluated.verification_status == VerificationStatus.VERIFIED

        # 4. Mandatory verbatim disclaimer must be present
        assert len(evaluated.limitation_disclaimers) >= 1
        assert MANDATORY_VERBATIM_DISCLAIMER in evaluated.limitation_disclaimers

    def test_clarification_2_scanned_only_document_never_receives_failed(self) -> None:
        """Clarification 2: Scanned-only document receives COMPLETED and REVIEW_REQUIRED, never FAILED."""
        page_prof = PageProfile(
            page_number=1,
            page_type=PageType.SCANNED,
            processing_status=PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR,
            table_presence=TablePresenceStatus.UNKNOWN_PENDING_OCR,
            printable_char_count=0,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.95,
            vector_line_count=0,
            deferred_regions_count=0,
        )
        report = _make_report(
            execution_state=JobExecutionState.COMPLETED,
            page_profiles=[page_prof],
            canonical_tables=[],
        )
        evaluated = evaluate_document_quality(report)

        # Execution succeeded, but data quality requires review for deferred OCR
        assert evaluated.execution_state == JobExecutionState.COMPLETED
        assert evaluated.verification_status == VerificationStatus.REVIEW_REQUIRED
        assert evaluated.verification_status != VerificationStatus.FAILED
        assert REASON_OCR_REQUIRED_FOR_SCANNED in evaluated.status_reason_codes
        assert REASON_NO_TABLES_FOUND not in evaluated.status_reason_codes

    def test_clarification_3_execution_failed_vs_quality_review_orthogonality(self) -> None:
        """Clarification 3: Execution failure vs data-quality status are independent and orthogonal."""
        # Case A: Operational abort -> JobExecutionState.FAILED, VerificationStatus.FAILED [EXECUTION_FAILED]
        report_failed = _make_report(execution_state=JobExecutionState.FAILED)
        status_f, reasons_f = evaluate_document_verification_status(report_failed)
        assert status_f == VerificationStatus.FAILED
        assert reasons_f == [REASON_EXECUTION_FAILED]

        # Case B: Operational success with data discrepancy -> COMPLETED, REVIEW_REQUIRED
        table = _make_table("tbl-disc", ["Item", "Amount"], [["Item", "10.00"], ["Total", "20.00"]])
        table.math_validation_outcome = ValidationOutcome.FAILED_VALIDATION
        report_review = _make_report(
            execution_state=JobExecutionState.COMPLETED,
            canonical_tables=[table],
        )
        status_r, reasons_r = evaluate_document_verification_status(report_review)
        assert report_review.execution_state == JobExecutionState.COMPLETED
        assert status_r == VerificationStatus.REVIEW_REQUIRED
        assert REASON_SOURCE_ARITHMETIC_DISCREPANCY in reasons_r

        # Case C: Operational success on fully inspected digital 0-table -> COMPLETED, FAILED [NO_TABLES_FOUND]
        digital_page = PageProfile(
            page_number=1,
            page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_ABSENT,
            printable_char_count=400,
            garbled_char_ratio=0.0,
            image_coverage_ratio=0.0,
            vector_line_count=0,
            deferred_regions_count=0,
        )
        report_zero = _make_report(
            execution_state=JobExecutionState.COMPLETED,
            page_profiles=[digital_page],
            canonical_tables=[],
        )
        status_z, reasons_z = evaluate_document_verification_status(report_zero)
        assert report_zero.execution_state == JobExecutionState.COMPLETED
        assert status_z == VerificationStatus.FAILED
        assert reasons_z == [REASON_NO_TABLES_FOUND]

    def test_clarification_4_formula_risk_boundary_no_apostrophes_and_negatives_numeric(self) -> None:
        """Clarification 4: Formula risk sets boolean flag only; no apostrophes prepended; negatives numeric."""
        # Formula injection candidate: sets flag, leaves raw/norm/accepted without apostrophe
        for prefix in ["=", "+", "-", "@", "\t", "\r"]:
            cell_formula = normalize_cell(f"{prefix}COMMAND")
            assert cell_formula["formula_risk_detected"] is True
            assert cell_formula["raw_value"] == f"{prefix}COMMAND"
            assert not cell_formula["accepted_value"].startswith("'")

        # Negative numbers remain numeric and never flag formula risk
        for neg_val in ["-123.45", "(123.45)", "123.45-", "-1,234.56"]:
            cell_num = normalize_cell(neg_val)
            assert cell_num["formula_risk_detected"] is False
            assert cell_num["data_type"] == DataType.DECIMAL
            assert cell_num["numeric_decimal"] is not None
            assert cell_num["numeric_decimal"] < 0
            assert not cell_num["accepted_value"].startswith("'")
