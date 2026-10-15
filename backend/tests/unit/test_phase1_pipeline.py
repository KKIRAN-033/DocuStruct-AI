"""DocuStruct AI — Unit Tests: End-to-End Phase 1 Pipeline

Tests full end-to-end processing across digital, nontable, scanned, hybrid, multipage,
duplicate, and arithmetic discrepancy layouts, security error containment, Windows
handle discipline, and workspace lifecycle in accordance with MASTER_DIRECTIVE.md
Sections 18, 19, and 20.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import pytest

from app.config.calibration import CalibrationConfig
from app.config.settings import AppSettings
from app.models.state import (
    CellQualityStatus,
    JobExecutionState,
    VerificationStatus,
)
from app.pipeline import run_phase1_pipeline
from app.verification.quality_gate import (
    MANDATORY_VERBATIM_DISCLAIMER,
    REASON_DEFERRED_REGIONS_REMAIN,
    REASON_NO_TABLES_FOUND,
    REASON_OCR_REQUIRED_FOR_SCANNED,
    REASON_SOURCE_ARITHMETIC_DISCREPANCY,
)


# ── Test Suite 1: End-to-End Extraction & Document Quality ──────────────────


class TestPhase1PipelineExecution:
    """Tests for complete pipeline runs across different document layouts."""

    def test_pipeline_digital_ruled_table(self, synthetic_ruled_table_pdf: Path) -> None:
        """Digital PDF with a ruled table extracts tables and achieves COMPLETED state."""
        report = run_phase1_pipeline(synthetic_ruled_table_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status in (
            VerificationStatus.VERIFIED,
            VerificationStatus.VERIFIED_WITH_WARNINGS,
        )
        assert len(report.canonical_tables) == 1
        assert len(report.page_profiles) == 1
        assert len(report.page_results) == 1
        assert MANDATORY_VERBATIM_DISCLAIMER in report.limitation_disclaimers

        # Check extracted table properties
        table = report.canonical_tables[0]
        assert len(table.rows) == 3  # Header + 2 data rows
        assert len(table.normalized_headers) == 3
        assert table.structural_checks_passed is True

    def test_pipeline_digital_no_tables(self, synthetic_nontable_pdf: Path) -> None:
        """Digital PDF with no extractable tables yields COMPLETED and FAILED with NO_TABLES_FOUND."""
        report = run_phase1_pipeline(synthetic_nontable_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status == VerificationStatus.FAILED
        assert REASON_NO_TABLES_FOUND in report.status_reason_codes
        assert len(report.canonical_tables) == 0
        assert MANDATORY_VERBATIM_DISCLAIMER in report.limitation_disclaimers

    def test_pipeline_scanned_pdf(self, synthetic_scanned_pdf: Path) -> None:
        """Scanned PDF yields COMPLETED and REVIEW_REQUIRED with OCR_REQUIRED_FOR_SCANNED_CONTENT."""
        report = run_phase1_pipeline(synthetic_scanned_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status == VerificationStatus.REVIEW_REQUIRED
        assert REASON_OCR_REQUIRED_FOR_SCANNED in report.status_reason_codes
        assert len(report.canonical_tables) == 0
        assert MANDATORY_VERBATIM_DISCLAIMER in report.limitation_disclaimers

    def test_pipeline_hybrid_pdf(self, synthetic_hybrid_pdf: Path) -> None:
        """Hybrid PDF with deferred regions yields COMPLETED and REVIEW_REQUIRED."""
        report = run_phase1_pipeline(synthetic_hybrid_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status == VerificationStatus.REVIEW_REQUIRED
        assert (
            REASON_DEFERRED_REGIONS_REMAIN in report.status_reason_codes
            or REASON_OCR_REQUIRED_FOR_SCANNED in report.status_reason_codes
        )

    def test_pipeline_multipage_continuation(
        self, synthetic_multipage_continuation_pdf: Path
    ) -> None:
        """2-page table with continuation stitches into a single canonical table."""
        report = run_phase1_pipeline(synthetic_multipage_continuation_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert len(report.canonical_tables) == 1

        stitched_table = report.canonical_tables[0]
        assert stitched_table.source_pages == [1, 2]
        # Page 1 had 4 rows (1 hdr + 3 data).
        # Page 2 had 5 rows (1 repeated hdr stripped + 3 data + 1 total).
        # Total rows = 4 + 4 = 8.
        assert len(stitched_table.rows) == 8

        # Verify contiguous row indices
        for expected_idx, row in enumerate(stitched_table.rows):
            for cell in row:
                assert cell.row_idx == expected_idx

    def test_pipeline_duplicate_rows_strictly_preserved(
        self, synthetic_duplicate_rows_pdf: Path
    ) -> None:
        """Identical transaction rows are preserved without deduplication."""
        report = run_phase1_pipeline(synthetic_duplicate_rows_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert len(report.canonical_tables) == 1

        table = report.canonical_tables[0]
        # Data had 4 rows: 1 header + 2 duplicate TX-901 rows + 1 TX-902 row
        assert len(table.rows) == 4
        assert table.rows[1][0].accepted_value == "TX-901"
        assert table.rows[2][0].accepted_value == "TX-901"

    def test_pipeline_arithmetic_discrepancy(
        self, synthetic_arithmetic_discrepancy_pdf: Path
    ) -> None:
        """Arithmetic discrepancy escalates to REVIEW_REQUIRED and preserves printed value."""
        report = run_phase1_pipeline(synthetic_arithmetic_discrepancy_pdf)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.verification_status == VerificationStatus.REVIEW_REQUIRED
        assert REASON_SOURCE_ARITHMETIC_DISCREPANCY in report.status_reason_codes

        table = report.canonical_tables[0]
        total_cell = table.rows[3][1]
        assert total_cell.raw_value == "350.00"
        assert total_cell.accepted_value == "350.00"
        assert total_cell.quality_status == CellQualityStatus.ANOMALY_FLAGGED


# ── Test Suite 2: Security Errors & Resource Lifecycle ──────────────────────


class TestPhase1PipelineSafetyAndErrors:
    """Tests for pipeline security exceptions, handle closure, and workspace cleanup."""

    def test_pipeline_corrupt_pdf_controlled_failure(self, corrupt_pdf_file: Path) -> None:
        """Corrupt PDF returns a controlled failure report instead of raising an unhandled exception."""
        report = run_phase1_pipeline(corrupt_pdf_file)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "CORRUPT_PDF" in report.status_reason_codes
        assert len(report.canonical_tables) == 0

    def test_pipeline_encrypted_pdf_controlled_failure(self, encrypted_pdf: Path) -> None:
        """Encrypted PDF returns controlled failure with ENCRYPTED_PDF reason."""
        report = run_phase1_pipeline(encrypted_pdf)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "ENCRYPTED_PDF" in report.status_reason_codes

    def test_pipeline_oversized_pdf_controlled_failure(self, oversized_file: Path) -> None:
        """Oversized PDF returns controlled failure with FILE_SIZE_EXCEEDED."""
        report = run_phase1_pipeline(oversized_file)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "FILE_SIZE_EXCEEDED" in report.status_reason_codes

    def test_pipeline_page_count_exceeded_controlled_failure(
        self, multipage_51_pdf: Path
    ) -> None:
        """PDF exceeding 50 pages returns controlled failure with PAGE_COUNT_EXCEEDED."""
        report = run_phase1_pipeline(multipage_51_pdf)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "PAGE_COUNT_EXCEEDED" in report.status_reason_codes

    def test_pipeline_nonexistent_file(self, tmp_path: Path) -> None:
        """Non-existent file returns controlled failure report with FILE_NOT_FOUND."""
        nonexistent = tmp_path / "does_not_exist.pdf"
        report = run_phase1_pipeline(nonexistent)

        assert report.execution_state == JobExecutionState.FAILED
        assert report.verification_status == VerificationStatus.FAILED
        assert "FILE_NOT_FOUND" in report.status_reason_codes

    def test_pipeline_workspace_cleaned_and_original_preserved(
        self, synthetic_ruled_table_pdf: Path, tmp_path: Path
    ) -> None:
        """Workspace is completely removed after execution while original PDF remains intact."""
        custom_workspace_root = tmp_path / "custom_workspaces"
        settings = AppSettings(workspace_root=custom_workspace_root)

        report = run_phase1_pipeline(synthetic_ruled_table_pdf, settings=settings)

        assert report.execution_state == JobExecutionState.COMPLETED
        # Original file must exist
        assert synthetic_ruled_table_pdf.exists()

        # Job workspace directory inside custom_workspace_root must be cleaned up
        job_workspace = custom_workspace_root / report.job_id
        assert not job_workspace.exists()

    def test_pipeline_cleanup_on_exception(
        self, synthetic_ruled_table_pdf: Path, tmp_path: Path
    ) -> None:
        """Workspace cleanup is guaranteed even when extraction raises an unexpected exception."""
        custom_workspace_root = tmp_path / "error_workspaces"
        settings = AppSettings(workspace_root=custom_workspace_root)

        with patch(
            "app.pipeline.extract_tables_from_page",
            side_effect=RuntimeError("Simulated extraction error"),
        ):
            report = run_phase1_pipeline(synthetic_ruled_table_pdf, settings=settings)

            assert report.execution_state == JobExecutionState.FAILED
            # Workspace must be cleaned up despite the exception
            job_workspace = custom_workspace_root / report.job_id
            assert not job_workspace.exists()
            assert synthetic_ruled_table_pdf.exists()

    def test_pipeline_memory_measurement_recorded(
        self, synthetic_ruled_table_pdf: Path
    ) -> None:
        """When enable_memory_measurement is True, peak_python_heap_bytes is recorded."""
        settings = AppSettings(enable_memory_measurement=True)
        report = run_phase1_pipeline(synthetic_ruled_table_pdf, settings=settings)

        assert report.execution_state == JobExecutionState.COMPLETED
        assert report.peak_python_heap_bytes is not None
        assert report.peak_python_heap_bytes > 0
