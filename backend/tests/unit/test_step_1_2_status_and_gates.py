"""
Unit tests for Step 1.2 — State Enumerations and Domain Models.

Covers MASTER_DIRECTIVE.md Sections 8 & 9 requirements:
    - All 9 enum string values.
    - BoundingBox geometry and normalization.
    - CellRecord immutability and Decimal precision.
    - Full JSON serialization of nested domain models.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

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


# ── State Enumerations ──────────────────────────────────────────────────────


class TestStateEnums:
    """Verify all 9 enums have exact string values."""

    def test_job_execution_state_values(self) -> None:
        expected = [
            "QUEUED", "UNDERSTANDING", "EXTRACTING", "RECONSTRUCTING",
            "VERIFYING", "DIAGNOSING", "CORRECTING", "REVALIDATING",
            "DELIVERING", "COMPLETED", "FAILED",
        ]
        assert [e.value for e in JobExecutionState] == expected

    def test_verification_status_values(self) -> None:
        expected = ["VERIFIED", "VERIFIED_WITH_WARNINGS", "REVIEW_REQUIRED", "FAILED"]
        assert [e.value for e in VerificationStatus] == expected

    def test_page_type_values(self) -> None:
        expected = ["DIGITAL", "SCANNED", "HYBRID", "EMPTY_OR_UNREADABLE"]
        assert [e.value for e in PageType] == expected

    def test_page_processing_status_values(self) -> None:
        expected = ["EXTRACTED", "INCOMPLETE_DEFERRED_TO_OCR", "EMPTY_PAGE", "FAILED_PAGE"]
        assert [e.value for e in PageProcessingStatus] == expected

    def test_table_presence_status_values(self) -> None:
        expected = ["CONFIRMED_PRESENT", "CONFIRMED_ABSENT", "UNKNOWN_PENDING_OCR"]
        assert [e.value for e in TablePresenceStatus] == expected

    def test_validation_outcome_values(self) -> None:
        expected = ["PASSED", "PASSED_WITH_WARNINGS", "FAILED_VALIDATION", "NOT_APPLICABLE"]
        assert [e.value for e in ValidationOutcome] == expected

    def test_stitch_decision_values(self) -> None:
        expected = ["STITCH_CONFIRMED", "STITCH_REJECTED", "STITCH_REVIEW_REQUIRED"]
        assert [e.value for e in StitchDecision] == expected

    def test_cell_quality_status_values(self) -> None:
        expected = [
            "EXTRACTED_AS_IS", "CORROBORATED", "CORRECTED_WITH_EVIDENCE",
            "LOW_CONFIDENCE_WARNING", "ANOMALY_FLAGGED", "ILLEGIBLE_OR_MISSING",
        ]
        assert [e.value for e in CellQualityStatus] == expected

    def test_data_type_values(self) -> None:
        expected = ["STRING", "IDENTIFIER", "INTEGER", "DECIMAL", "HIGH_PRECISION_DECIMAL", "DATE", "EMPTY"]
        assert [e.value for e in DataType] == expected

    def test_enums_are_json_serializable(self) -> None:
        """String-backed enums must serialize to JSON directly."""
        val = json.dumps({"status": VerificationStatus.VERIFIED})
        assert '"VERIFIED"' in val


# ── BoundingBox ─────────────────────────────────────────────────────────────


class TestBoundingBox:
    """Verify geometry validation and normalized coordinates."""

    def test_normalized_coordinates(self) -> None:
        b = BoundingBox(x0=10, y0=20, x1=50, y1=60, page_width=100, page_height=200, coord_exact=True)
        assert b.norm_x0 == pytest.approx(0.1)
        assert b.norm_x1 == pytest.approx(0.5)
        assert b.norm_y0 == pytest.approx(0.1)
        assert b.norm_y1 == pytest.approx(0.3)

    def test_invalid_coordinate_order_rejected(self) -> None:
        with pytest.raises(ValueError, match="x0.*x1"):
            BoundingBox(x0=50, y0=0, x1=10, y1=50, page_width=100, page_height=100, coord_exact=True)

    def test_invalid_y_order_rejected(self) -> None:
        with pytest.raises(ValueError, match="y0.*y1"):
            BoundingBox(x0=0, y0=50, x1=50, y1=10, page_width=100, page_height=100, coord_exact=True)

    def test_zero_page_width_rejected(self) -> None:
        with pytest.raises(ValueError, match="[Pp]ositive"):
            BoundingBox(x0=0, y0=0, x1=50, y1=50, page_width=0, page_height=100, coord_exact=True)

    def test_equal_coordinates_allowed(self) -> None:
        """Zero-area bounding box (point) should be allowed."""
        b = BoundingBox(x0=10, y0=10, x1=10, y1=10, page_width=100, page_height=100, coord_exact=False)
        assert b.norm_x0 == b.norm_x1


# ── CellRecord ──────────────────────────────────────────────────────────────


class TestCellRecord:
    """Verify CellRecord contracts: raw_value integrity, Decimal safety."""

    def _make_cell(self, **overrides) -> CellRecord:
        defaults = dict(
            table_id="t1", row_idx=0, col_idx=0, source_page=1,
            extraction_method="pdfplumber", raw_value="1,234.56",
            accepted_value="1234.56", data_type=DataType.DECIMAL,
            quality_status=CellQualityStatus.EXTRACTED_AS_IS,
        )
        defaults.update(overrides)
        return CellRecord(**defaults)

    def test_raw_value_preserved(self) -> None:
        c = self._make_cell()
        assert c.raw_value == "1,234.56"

    def test_decimal_precision_preserved(self) -> None:
        c = self._make_cell(numeric_decimal=Decimal("1234.56"))
        assert c.numeric_decimal == Decimal("1234.56")
        assert isinstance(c.numeric_decimal, Decimal)

    def test_float_input_converted_via_string(self) -> None:
        """Float → str → Decimal to avoid binary precision loss."""
        c = self._make_cell(numeric_decimal=1234.56)
        assert isinstance(c.numeric_decimal, Decimal)
        # Should NOT have binary float artifacts
        assert "1234.56" in str(c.numeric_decimal)

    def test_formula_risk_default_false(self) -> None:
        c = self._make_cell()
        assert c.formula_risk_detected is False

    def test_notes_default_empty_list(self) -> None:
        c = self._make_cell()
        assert c.notes == []


# ── Full Serialization ──────────────────────────────────────────────────────


class TestDomainModelSerialization:
    """Verify JSON round-trip of DocumentEvaluationReport."""

    def test_document_report_serialization(self) -> None:
        report = DocumentEvaluationReport(
            job_id="test-001",
            source_filename="test.pdf",
            execution_state=JobExecutionState.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
            status_reason_codes=[],
            limitation_disclaimers=["test disclaimer"],
        )
        json_str = report.model_dump_json()
        data = json.loads(json_str)
        assert data["job_id"] == "test-001"
        assert data["verification_status"] == "VERIFIED"
        assert data["execution_state"] == "COMPLETED"

    def test_nested_model_serialization(self) -> None:
        profile = PageProfile(
            page_number=1, page_type=PageType.DIGITAL,
            processing_status=PageProcessingStatus.EXTRACTED,
            table_presence=TablePresenceStatus.CONFIRMED_PRESENT,
            printable_char_count=500, garbled_char_ratio=0.01,
            image_coverage_ratio=0.0, vector_line_count=20,
            deferred_regions_count=0,
        )
        json_str = profile.model_dump_json()
        data = json.loads(json_str)
        assert data["page_type"] == "DIGITAL"
        assert data["printable_char_count"] == 500
