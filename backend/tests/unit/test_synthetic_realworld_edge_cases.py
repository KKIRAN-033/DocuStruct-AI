"""DocuStruct AI — Synthetic Regression Test Suite for Document Edge Cases.

WARNING / AUDIT DISTINCTION:
These test cases use SYNTHETIC PDF documents generated programmatically via PyMuPDF.
They validate edge-case handling (blank cells, duplicate headers, Indian numbering,
accounting negatives, 0-byte files, OCR deferrals, and multipage continuations) within
the deterministic pipeline. They DO NOT constitute empirical real-world validation on
uncontrolled external reference documents. Real-world accuracy remains UNMEASURED until
an independent, manually verified reference benchmark is evaluated.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import pymupdf
import pytest

from app.models.state import (
    CellQualityStatus,
    JobExecutionState,
    ValidationOutcome,
    VerificationStatus,
)
from app.pipeline import run_phase1_pipeline
from app.verification.quality_gate import (
    MANDATORY_VERBATIM_DISCLAIMER,
    REASON_OCR_REQUIRED_FOR_SCANNED,
)


class TestSyntheticDocumentEdgeCases:
    """Safe, deterministic regression tests for document edge cases using synthetic fixtures."""

    def test_synthetic_empty_zero_byte_file_rejection(self, tmp_path: Path) -> None:
        """A zero-byte file is rejected cleanly with a controlled failure report."""
        empty_pdf = tmp_path / "synthetic_zero_byte.pdf"
        empty_pdf.write_bytes(b"")

        report = run_phase1_pipeline(empty_pdf)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "INVALID_FILE_TYPE" in report.status_reason_codes or "ZERO_PAGE_PDF" in report.status_reason_codes
        assert len(report.canonical_tables) == 0

    def test_synthetic_table_with_interior_blank_cells(self, tmp_path: Path) -> None:
        """A ruled table containing blank cells preserves empty strings without column misalignment."""
        pdf_path = tmp_path / "synthetic_blank_cells.pdf"
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=612, height=792)
            x_start, y_start = 50, 100
            col_w, row_h = 150, 30
            cols, rows = 3, 3

            for r in range(rows + 1):
                y = y_start + r * row_h
                page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
            for c in range(cols + 1):
                x = x_start + c * col_w
                page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

            # Row 0: Headers
            page.insert_text((x_start + 10, y_start + 20), "Item", fontsize=9)
            page.insert_text((x_start + col_w + 10, y_start + 20), "Code", fontsize=9)
            page.insert_text((x_start + 2 * col_w + 10, y_start + 20), "Amount", fontsize=9)

            # Row 1: Code is blank
            page.insert_text((x_start + 10, y_start + row_h + 20), "Product A", fontsize=9)
            page.insert_text((x_start + 2 * col_w + 10, y_start + row_h + 20), "150.00", fontsize=9)

            # Row 2: Item is blank, Amount is blank
            page.insert_text((x_start + col_w + 10, y_start + 2 * row_h + 20), "MISC-99", fontsize=9)

            doc.save(str(pdf_path))
        finally:
            doc.close()

        report = run_phase1_pipeline(pdf_path)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert len(report.canonical_tables) == 1

        table = report.canonical_tables[0]
        assert len(table.rows) == 3
        assert len(table.normalized_headers) == 3

        # Row 1 check: Col 1 is empty string
        row1_vals = [c.accepted_value for c in table.rows[1]]
        assert row1_vals[0] == "Product A"
        assert row1_vals[1] == ""
        assert row1_vals[2] == "150.00"

        # Row 2 check: Col 0 and Col 2 are empty strings
        row2_vals = [c.accepted_value for c in table.rows[2]]
        assert row2_vals[0] == ""
        assert row2_vals[1] == "MISC-99"
        assert row2_vals[2] == ""

    def test_synthetic_table_duplicate_headers_preserved_losslessly(self, tmp_path: Path) -> None:
        """Tables with duplicate header labels are preserved losslessly without key collisions."""
        pdf_path = tmp_path / "synthetic_duplicate_headers.pdf"
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=612, height=792)
            x_start, y_start = 50, 100
            col_w, row_h = 150, 30
            cols, rows = 3, 2

            for r in range(rows + 1):
                y = y_start + r * row_h
                page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
            for c in range(cols + 1):
                x = x_start + c * col_w
                page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

            # Duplicate header strings: Period, Amount, Amount
            page.insert_text((x_start + 10, y_start + 20), "Period", fontsize=9)
            page.insert_text((x_start + col_w + 10, y_start + 20), "Amount", fontsize=9)
            page.insert_text((x_start + 2 * col_w + 10, y_start + 20), "Amount", fontsize=9)

            page.insert_text((x_start + 10, y_start + row_h + 20), "2026-Q1", fontsize=9)
            page.insert_text((x_start + col_w + 10, y_start + row_h + 20), "1,200.00", fontsize=9)
            page.insert_text((x_start + 2 * col_w + 10, y_start + row_h + 20), "2,400.00", fontsize=9)

            doc.save(str(pdf_path))
        finally:
            doc.close()

        report = run_phase1_pipeline(pdf_path)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert len(report.canonical_tables) == 1

        table = report.canonical_tables[0]
        assert table.original_headers == ["Period", "Amount", "Amount"]
        assert table.normalized_headers == ["Period", "Amount", "Amount"]
        assert [c.raw_value for c in table.rows[1]] == ["2026-Q1", "1,200.00", "2,400.00"]
        assert [c.accepted_value for c in table.rows[1]] == ["2026-Q1", "1200.00", "2400.00"]

    def test_synthetic_indian_numbering_and_accounting_negatives_math(self, tmp_path: Path) -> None:
        """Indian numbering and accounting negatives evaluate accurately via exact Decimal arithmetic."""
        pdf_path = tmp_path / "synthetic_indian_accounting.pdf"
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=612, height=792)
            x_start, y_start = 50, 100
            col_w, row_h = 150, 30
            cols, rows = 3, 4

            for r in range(rows + 1):
                y = y_start + r * row_h
                page.draw_line(pymupdf.Point(x_start, y), pymupdf.Point(x_start + cols * col_w, y))
            for c in range(cols + 1):
                x = x_start + c * col_w
                page.draw_line(pymupdf.Point(x, y_start), pymupdf.Point(x, y_start + rows * row_h))

            # 1,50,000.00 + (50,000.00) = 1,00,000.00
            data = [
                ["Account", "Category", "Amount"],
                ["ACC-01", "Credit", "1,50,000.00"],
                ["ACC-02", "Debit", "(50,000.00)"],
                ["Total", "Net", "1,00,000.00"],
            ]

            for r, row in enumerate(data):
                for c, cell in enumerate(row):
                    page.insert_text((x_start + c * col_w + 10, y_start + r * row_h + 20), cell, fontsize=9)

            doc.save(str(pdf_path))
        finally:
            doc.close()

        report = run_phase1_pipeline(pdf_path)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert len(report.canonical_tables) == 1

        table = report.canonical_tables[0]
        assert table.math_validation_outcome == ValidationOutcome.PASSED
        assert report.verification_status == VerificationStatus.VERIFIED
        assert MANDATORY_VERBATIM_DISCLAIMER in report.limitation_disclaimers
        assert len(report.validation_issues) == 0

    def test_synthetic_scanned_page_strictly_defers_to_ocr(self, tmp_path: Path) -> None:
        """Scanned raster images are truthfully detected and deferred with OCR_REQUIRED_FOR_SCANNED_CONTENT."""
        pdf_path = tmp_path / "synthetic_scanned_deferral.pdf"
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=500, height=500)
            # Insert large raster image covering >60%
            pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 50, 50), False)
            page.insert_image(pymupdf.Rect(50, 50, 450, 450), pixmap=pix)
            doc.save(str(pdf_path))
        finally:
            doc.close()

        report = run_phase1_pipeline(pdf_path)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status == VerificationStatus.REVIEW_REQUIRED
        assert REASON_OCR_REQUIRED_FOR_SCANNED in report.status_reason_codes
        assert len(report.canonical_tables) == 0
        assert report.page_profiles[0].page_type.value == "SCANNED"
        assert report.page_profiles[0].processing_status.value == "INCOMPLETE_DEFERRED_TO_OCR"
