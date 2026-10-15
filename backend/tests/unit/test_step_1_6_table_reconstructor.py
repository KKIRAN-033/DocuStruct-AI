"""
DocuStruct AI — Unit Tests: Step 1.6 Multipage Table Reconstructor

Tests 7-factor stitch evaluation, table-relative column overlap,
sliding-window header stripping (1–3 rows), multipage table stitching,
duplicate row preservation, evidence-gated cell corrections, and
prohibition of auto-balancing totals in accordance with MASTER_DIRECTIVE.md
Sections 14 and 15.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.config.calibration import CalibrationConfig
from app.extraction.normalizer import normalize_cell
from app.extraction.table_reconstructor import (
    PERMITTED_EVIDENCE_SOURCES,
    apply_evidence_gated_correction,
    compute_column_overlap_ratio,
    compute_relative_column_intervals,
    compute_type_compatibility,
    evaluate_header_similarity,
    evaluate_stitch_pair,
    reconstruct_multipage_tables,
    stitch_canonical_tables,
    strip_repeated_headers,
)
from app.models.domain import (
    BoundingBox,
    CanonicalTable,
    CellRecord,
    CorrectionRecord,
    StitchAuditEvent,
)
from app.models.state import (
    CellQualityStatus,
    DataType,
    StitchDecision,
)


# ─── Helper Functions ────────────────────────────────────────────────────


def _create_cell(
    table_id: str,
    row_idx: int,
    col_idx: int,
    page_num: int,
    text: str,
    bbox: BoundingBox | None = None,
) -> CellRecord:
    """Helper to create a validated normalized CellRecord."""
    norm = normalize_cell(text)
    return CellRecord(
        table_id=table_id,
        row_idx=row_idx,
        col_idx=col_idx,
        source_page=page_num,
        bbox=bbox,
        extraction_method="LINE_BASED_RULING",
        raw_value=norm["raw_value"],
        normalized_value=norm["normalized_value"],
        accepted_value=norm["accepted_value"],
        numeric_decimal=norm["numeric_decimal"],
        data_type=norm["data_type"],
        quality_status=CellQualityStatus.EXTRACTED_AS_IS,
        formula_risk_detected=norm["formula_risk_detected"],
    )


def _build_test_table(
    table_id: str,
    page_num: int,
    headers: list[str],
    data_rows: list[list[str]],
    x_offset: float = 50.0,
    col_widths: list[float] | None = None,
) -> CanonicalTable:
    """Construct a synthetic CanonicalTable with accurate bounding box geometry."""
    if col_widths is None:
        col_widths = [100.0] * len(headers)

    pw, ph = 612.0, 792.0
    all_rows: list[list[CellRecord]] = []
    y_start = 100.0
    row_h = 25.0

    # Header row at index 0
    hdr_cells: list[CellRecord] = []
    current_x = x_offset
    for c_idx, h_text in enumerate(headers):
        w = col_widths[c_idx]
        bbox = BoundingBox(
            x0=current_x,
            y0=y_start,
            x1=current_x + w,
            y1=y_start + row_h,
            page_width=pw,
            page_height=ph,
            coord_exact=True,
        )
        cell = _create_cell(table_id, 0, c_idx, page_num, h_text, bbox)
        hdr_cells.append(cell)
        current_x += w
    all_rows.append(hdr_cells)

    # Data rows
    for r_idx, row_values in enumerate(data_rows, start=1):
        r_cells: list[CellRecord] = []
        current_x = x_offset
        y_pos = y_start + r_idx * row_h
        for c_idx, val in enumerate(row_values):
            w = col_widths[c_idx]
            bbox = BoundingBox(
                x0=current_x,
                y0=y_pos,
                x1=current_x + w,
                y1=y_pos + row_h,
                page_width=pw,
                page_height=ph,
                coord_exact=True,
            )
            cell = _create_cell(table_id, r_idx, c_idx, page_num, val, bbox)
            r_cells.append(cell)
            current_x += w
        all_rows.append(r_cells)

    total_w = sum(col_widths)
    table_bbox = BoundingBox(
        x0=x_offset,
        y0=y_start,
        x1=x_offset + total_w,
        y1=y_start + len(all_rows) * row_h,
        page_width=pw,
        page_height=ph,
        coord_exact=True,
    )

    return CanonicalTable(
        table_id=table_id,
        source_pages=[page_num],
        page_bbox=table_bbox,
        original_headers=headers,
        normalized_headers=[h.strip() for h in headers],
        header_row_count=1,
        rows=all_rows,
        extraction_method="LINE_BASED_RULING",
        structural_checks_passed=True,
    )


# ─── TestColumnOverlapAndGeometry ────────────────────────────────────────


class TestColumnOverlapAndGeometry:
    def test_identical_intervals_overlap_ratio(self):
        intervals = [(0.0, 0.33), (0.33, 0.66), (0.66, 1.0)]
        overlap = compute_column_overlap_ratio(intervals, intervals)
        assert overlap == 1.0

    def test_disjoint_intervals_overlap_ratio(self):
        a = [(0.0, 0.25), (0.25, 0.5)]
        b = [(0.6, 0.8), (0.8, 1.0)]
        overlap = compute_column_overlap_ratio(a, b)
        assert overlap == 0.0

    def test_differing_column_counts_overlap_zero(self):
        a = [(0.0, 0.5), (0.5, 1.0)]
        b = [(0.0, 0.33), (0.33, 0.66), (0.66, 1.0)]
        assert compute_column_overlap_ratio(a, b) == 0.0

    def test_table_relative_normalization_handles_margin_shift(self):
        # Table 1 has page margin x_offset=50, Table 2 has margin x_offset=80 (odd/even page shift)
        # Both have identical relative widths [100, 200, 100]
        t1 = _build_test_table("t1", 1, ["A", "B", "C"], [["1", "2", "3"]], x_offset=50.0, col_widths=[100.0, 200.0, 100.0])
        t2 = _build_test_table("t2", 2, ["A", "B", "C"], [["4", "5", "6"]], x_offset=80.0, col_widths=[100.0, 200.0, 100.0])

        inv1 = compute_relative_column_intervals(t1)
        inv2 = compute_relative_column_intervals(t2)
        overlap = compute_column_overlap_ratio(inv1, inv2)
        # Because coordinates are normalized relative to table span, overlap is 1.0!
        assert overlap == 1.0


# ─── TestHeaderSimilarityAndStripping ────────────────────────────────────


class TestHeaderSimilarityAndStripping:
    def test_exact_header_similarity(self):
        h1 = ["Account No", "Description", "Balance"]
        h2 = ["Account No", "Description", "Balance"]
        assert evaluate_header_similarity(h1, h2) == 1.0

    def test_fuzzy_header_similarity(self):
        h1 = ["Account Number", "Transaction Details", "Total Amount"]
        h2 = ["Account No", "Transaction Detail", "Total Amt"]
        score = evaluate_header_similarity(h1, h2)
        assert score >= 0.75

    def test_strip_single_row_repeated_header(self):
        headers = ["Item", "Qty", "Price"]
        t2 = _build_test_table("t2", 2, headers, [
            ["Item", "Qty", "Price"],  # Repeated header at index 0 of body
            ["Widget A", "10", "15.00"],
            ["Widget B", "5", "25.00"],
        ])
        # In lower table, rows[1] is repeated header
        remaining, stripped = strip_repeated_headers(headers, t2.rows[1:])
        assert stripped == 1
        assert len(remaining) == 2
        assert remaining[0][0].accepted_value == "Widget A"

    def test_data_row_not_mistaken_for_header(self):
        headers = ["Item", "Qty", "Price"]
        t2 = _build_test_table("t2", 2, headers, [
            ["Hardware 101", "100", "50.00"],  # Regular data row
            ["Hardware 102", "200", "75.00"],
        ])
        remaining, stripped = strip_repeated_headers(headers, t2.rows[1:])
        assert stripped == 0
        assert len(remaining) == 2


# ─── Test7FactorDecisionEngine ───────────────────────────────────────────


class Test7FactorDecisionEngine:
    def test_confirmed_continuation(self):
        t1 = _build_test_table("t1", 1, ["ID", "Name", "Total"], [
            ["1", "Alpha", "100.00"],
            ["2", "Beta", "200.00"],
        ])
        t2 = _build_test_table("t2", 2, ["ID", "Name", "Total"], [
            ["3", "Gamma", "300.00"],
            ["4", "Delta", "400.00"],
        ])
        decision, audit = evaluate_stitch_pair(t1, t2)
        assert decision == StitchDecision.STITCH_CONFIRMED
        assert audit.decision == StitchDecision.STITCH_CONFIRMED
        assert audit.col_overlap_ratio >= 0.75
        assert audit.type_compatibility_ratio >= 0.85
        assert "SERIAL_CONTINUITY_CONTINUOUS_SEQUENCE" in audit.reasons

    def test_rejected_nonsequential_pages(self):
        t1 = _build_test_table("t1", 1, ["A", "B"], [["1", "2"]])
        t2 = _build_test_table("t2", 3, ["A", "B"], [["3", "4"]])  # Page 3, not 2
        decision, audit = evaluate_stitch_pair(t1, t2)
        assert decision == StitchDecision.STITCH_REJECTED
        assert "PAGES_NOT_SEQUENTIAL" in audit.reasons

    def test_rejected_differing_columns_with_grand_total(self):
        t1 = _build_test_table("t1", 1, ["Item", "Amount"], [
            ["Service Fee", "150.00"],
            ["Grand Total", "150.00"],  # Ends with Grand Total
        ])
        t2 = _build_test_table("t2", 2, ["Code", "Description", "Cost"], [
            ["X01", "Part A", "25.00"],
        ])
        decision, audit = evaluate_stitch_pair(t1, t2)
        assert decision == StitchDecision.STITCH_REJECTED
        assert "DIFFERING_COLUMN_COUNTS_UPPER_TABLE_ENDS_WITH_TOTAL" in audit.reasons

    def test_review_required_differing_columns_without_total(self):
        t1 = _build_test_table("t1", 1, ["A", "B", "C"], [["1", "2", "3"]])
        t2 = _build_test_table("t2", 2, ["A", "B"], [["4", "5"]])
        decision, audit = evaluate_stitch_pair(t1, t2)
        assert decision == StitchDecision.STITCH_REVIEW_REQUIRED
        assert "DIFFERING_COLUMN_COUNTS_POTENTIAL_EXTRACTION_ARTIFACT" in audit.reasons

    def test_rejected_incompatible_data_types(self):
        # Column 1 in t1 is pure integer/decimal; Column 1 in t2 is long descriptive text
        t1 = _build_test_table("t1", 1, ["Name", "Amount"], [["A", "100.50"], ["B", "200.50"]])
        t2 = _build_test_table("t2", 2, ["Name", "Amount"], [["C", "Narrative note text"], ["D", "Another note"]])
        # Force column overlap to be disjoint
        t2.rows[0][1].bbox = BoundingBox(x0=400, y0=100, x1=500, y1=125, page_width=612, page_height=792, coord_exact=True)
        t2.page_bbox = BoundingBox(x0=50, y0=100, x1=500, y1=200, page_width=612, page_height=792, coord_exact=True)
        decision, audit = evaluate_stitch_pair(t1, t2)
        # Should be REJECTED or REVIEW_REQUIRED based on type/overlap
        assert decision in (StitchDecision.STITCH_REJECTED, StitchDecision.STITCH_REVIEW_REQUIRED)


# ─── TestMultipageReconstruction ─────────────────────────────────────────


class TestMultipageReconstruction:
    def test_reconstruct_stitches_confirmed_chain(self):
        t1 = _build_test_table("tbl_p1_0", 1, ["No", "Desc", "Price"], [
            ["1", "Apple", "1.50"],
            ["2", "Banana", "2.00"],
        ])
        t2 = _build_test_table("tbl_p2_0", 2, ["No", "Desc", "Price"], [
            ["3", "Cherry", "3.00"],
            ["4", "Date", "4.00"],
        ])

        results = reconstruct_multipage_tables([t1, t2])
        assert len(results) == 1
        stitched = results[0]
        assert stitched.table_id == "tbl_p1_0"
        assert stitched.source_pages == [1, 2]
        # Total rows: header + 2 from t1 + (header stripped from t2) + 2 from t2 = 5 rows
        assert len(stitched.rows) == 5

        # Verify contiguous row indices
        for expected_idx, row in enumerate(stitched.rows):
            for cell in row:
                assert cell.row_idx == expected_idx

    def test_duplicate_rows_strictly_preserved(self):
        """Invariant: Identical transaction rows across pages must NEVER be pruned."""
        t1 = _build_test_table("tbl_p1_0", 1, ["Date", "Item", "Amount"], [
            ["2026-10-01", "Hardware", "100.00"],
            ["2026-10-01", "Hardware", "100.00"],  # Duplicate in t1
        ])
        t2 = _build_test_table("tbl_p2_0", 2, ["Date", "Item", "Amount"], [
            ["2026-10-01", "Hardware", "100.00"],  # Duplicate continuing in t2
            ["2026-10-02", "Software", "500.00"],
        ])

        results = reconstruct_multipage_tables([t1, t2])
        assert len(results) == 1
        stitched = results[0]
        # All duplicate rows must be present: 1 header + 2 from t1 + 2 from t2 = 5 rows
        assert len(stitched.rows) == 5
        hardware_rows = [r for r in stitched.rows[1:] if r[1].accepted_value == "Hardware"]
        assert len(hardware_rows) == 3


# ─── TestEvidenceGatedCorrections ────────────────────────────────────────


class TestEvidenceGatedCorrections:
    def test_valid_native_char_stream_correction(self):
        cell = _create_cell("t1", 1, 1, 1, "1234")
        updated_cell, record = apply_evidence_gated_correction(
            cell=cell,
            proposed_value="1,234.50",
            evidence_source="NATIVE_PDF_CHAR_STREAM",
            evidence_summary="Discovered missing decimal cents in native PDF text stream",
        )
        assert record is not None
        assert isinstance(record, CorrectionRecord)
        assert record.decision == "CORRECTION_ACCEPTED"
        assert record.inferred_candidate_only is False
        assert record.resulting_cell_status == CellQualityStatus.CORRECTED_WITH_EVIDENCE

        # Cell verification
        assert updated_cell.raw_value == "1234"  # raw_value remains immutable
        assert updated_cell.accepted_value == "1234.50"
        assert updated_cell.numeric_decimal == Decimal("1234.50")
        assert updated_cell.quality_status == CellQualityStatus.CORRECTED_WITH_EVIDENCE

    def test_unapproved_evidence_source_rejected(self):
        cell = _create_cell("t1", 1, 1, 1, "1234")
        updated_cell, record = apply_evidence_gated_correction(
            cell=cell,
            proposed_value="5000",
            evidence_source="LLM_HALLUCINATED_INFERENCE",  # Not in permitted sources
            evidence_summary="Model guessed a value",
        )
        assert record is None
        assert updated_cell.accepted_value == "1234"
        assert updated_cell.quality_status == CellQualityStatus.EXTRACTED_AS_IS

    def test_algebraic_inference_stored_only_in_candidate(self):
        """Invariant: Algebraic deductions must NEVER overwrite accepted values."""
        cell = _create_cell("t1", 2, 2, 1, "")  # Blank cell in source
        updated_cell, record = apply_evidence_gated_correction(
            cell=cell,
            proposed_value="300.00",
            evidence_source="VECTOR_GRID_GEOMETRY",
            evidence_summary="Deduced from row sum formula",
            is_algebraic_inference=True,
        )
        assert record is not None
        assert record.inferred_candidate_only is True
        assert record.decision == "INFERRED_CANDIDATE_RECORDED"
        assert record.resulting_cell_status == CellQualityStatus.ILLEGIBLE_OR_MISSING

        # Accepted value is NOT modified to the candidate
        assert updated_cell.accepted_value == ""
        assert updated_cell.inferred_candidate_value == "300.00"
        assert updated_cell.quality_status == CellQualityStatus.ILLEGIBLE_OR_MISSING


# ─── TestProhibitedAutoBalancingAndInference ──────────────────────────────


class TestProhibitedAutoBalancingAndInference:
    def test_auto_balancing_is_prohibited(self):
        """Section 15: 100 + 200 = 350 must preserve 350 and never replace with 300."""
        total_cell = _create_cell("t1", 3, 2, 1, "350.00")
        # Ensure that no automatic correction replaces 350 with 300
        # If someone attempted an algebraic correction:
        updated_cell, record = apply_evidence_gated_correction(
            cell=total_cell,
            proposed_value="300.00",
            evidence_source="VECTOR_GRID_GEOMETRY",
            evidence_summary="Sum of preceding rows equals 300",
            is_algebraic_inference=True,
        )
        # Accepted value remains 350.00
        assert updated_cell.accepted_value == "350.00"
        assert updated_cell.raw_value == "350.00"
        assert updated_cell.inferred_candidate_value == "300.00"


# ─── TestStitchAuditEvents ───────────────────────────────────────────────


class TestStitchAuditEvents:
    def test_audit_event_fields_complete(self):
        t1 = _build_test_table("t1", 1, ["A", "B"], [["1", "2"]])
        t2 = _build_test_table("t2", 2, ["A", "B"], [["3", "4"]])
        _, audit = evaluate_stitch_pair(t1, t2)

        assert isinstance(audit, StitchAuditEvent)
        assert audit.upper_table_id == "t1"
        assert audit.lower_table_id == "t2"
        assert audit.upper_page == 1
        assert audit.lower_page == 2
        assert isinstance(audit.decision, StitchDecision)
        assert 0.0 <= audit.header_similarity_score <= 1.0
        assert 0.0 <= audit.col_overlap_ratio <= 1.0
        assert 0.0 <= audit.type_compatibility_ratio <= 1.0
        assert len(audit.reasons) > 0
