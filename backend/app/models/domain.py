"""
DocuStruct AI — Domain Models

Typed, validated Pydantic v2 models implementing the data contracts
defined in MASTER_DIRECTIVE.md Section 9.

Design invariants:
    - ``raw_value`` is immutable — normalisation never overwrites it.
    - ``Decimal`` values are never round-tripped through binary float.
    - Identifiers preserve significant leading zeros.
    - Legitimate duplicate and ragged rows are never pruned or padded.
    - Coordinates use PDF points, zero-based relative to the page.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

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


# ── A. BoundingBox ──────────────────────────────────────────────────────────


class BoundingBox(BaseModel):
    """Spatial coordinates of a region on a PDF page.

    Coordinates are in PDF points (1/72 inch), zero-based relative
    to the lower-left corner of the page.

    Attributes
    ----------
    coord_exact : bool
        ``True`` when coordinates come from vector/character data;
        ``False`` when interpolated or estimated.
    """

    x0: float
    y0: float
    x1: float
    y1: float
    page_width: float
    page_height: float
    coord_exact: bool

    @model_validator(mode="after")
    def _validate_geometry(self) -> "BoundingBox":
        if self.page_width <= 0 or self.page_height <= 0:
            raise ValueError(
                f"Page dimensions must be positive: "
                f"width={self.page_width}, height={self.page_height}"
            )
        if self.x0 > self.x1:
            raise ValueError(f"x0 ({self.x0}) must be <= x1 ({self.x1})")
        if self.y0 > self.y1:
            raise ValueError(f"y0 ({self.y0}) must be <= y1 ({self.y1})")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def norm_x0(self) -> float:
        """X0 normalised to [0, 1] relative to page width."""
        return self.x0 / self.page_width

    @computed_field  # type: ignore[misc]
    @property
    def norm_x1(self) -> float:
        """X1 normalised to [0, 1] relative to page width."""
        return self.x1 / self.page_width

    @computed_field  # type: ignore[misc]
    @property
    def norm_y0(self) -> float:
        """Y0 normalised to [0, 1] relative to page height."""
        return self.y0 / self.page_height

    @computed_field  # type: ignore[misc]
    @property
    def norm_y1(self) -> float:
        """Y1 normalised to [0, 1] relative to page height."""
        return self.y1 / self.page_height


# ── B. CellRecord ──────────────────────────────────────────────────────────


class CellRecord(BaseModel):
    """Single cell extracted from a table.

    Contracts
    ---------
    - ``raw_value`` is the exact original extracted text and must
      never be overwritten by normalisation or correction.
    - ``numeric_decimal`` must not be converted through binary
      ``float`` — construct via ``Decimal(str_value)`` only.
    - ``accepted_value`` is the downstream-consumable value.
    - ``inferred_candidate_value`` is NOT an accepted correction.
    - ``row_idx`` and ``col_idx`` are 0-based.
    """

    table_id: str
    row_idx: int = Field(ge=0, description="0-based row index.")
    col_idx: int = Field(ge=0, description="0-based column index.")
    source_page: int = Field(ge=1, description="1-based PDF page number.")
    bbox: Optional[BoundingBox] = None
    extraction_method: str
    ocr_confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0,
        description="OCR confidence (None in Phase 1 — no OCR).",
    )

    # Value chain — raw_value is immutable
    raw_value: str
    normalized_value: Optional[str] = None
    numeric_decimal: Optional[Decimal] = None
    accepted_value: str
    inferred_candidate_value: Optional[str] = None

    data_type: DataType
    quality_status: CellQualityStatus
    formula_risk_detected: bool = False
    notes: list[str] = Field(default_factory=list)

    @field_validator("numeric_decimal", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: Any) -> Optional[Decimal]:
        """Ensure Decimal is constructed from string, never float."""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, float):
            # Convert float → str → Decimal to avoid binary precision loss
            return Decimal(str(value))
        return Decimal(str(value))


# ── C. StitchAuditEvent ────────────────────────────────────────────────────


class StitchAuditEvent(BaseModel):
    """Audit trail entry for a multipage table stitching decision."""

    upper_table_id: str
    lower_table_id: str
    upper_page: int = Field(ge=1)
    lower_page: int = Field(ge=1)
    decision: StitchDecision
    header_similarity_score: float = Field(ge=0.0, le=1.0)
    col_overlap_ratio: float = Field(ge=0.0, le=1.0)
    type_compatibility_ratio: float = Field(ge=0.0, le=1.0)
    repeated_header_rows_stripped: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


# ── D. ValidationIssue ─────────────────────────────────────────────────────


class ValidationIssue(BaseModel):
    """Issue discovered during arithmetic or structural validation.

    ``row_idx`` and ``col_idx`` are optional to allow table-level
    issues that do not map to a single cell.
    """

    issue_id: str
    table_id: str
    source_page: int = Field(ge=1)
    row_idx: Optional[int] = None
    col_idx: Optional[int] = None
    issue_code: str
    severity: str
    description: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    resolved: bool = False


# ── E. CorrectionRecord ───────────────────────────────────────────────────


class CorrectionRecord(BaseModel):
    """Audit trail for an evidence-gated cell correction.

    A correction is only accepted when backed by independent
    deterministic evidence from a permitted source
    (``NATIVE_PDF_CHAR_STREAM``, ``INDEPENDENT_WORD_COORDINATES``,
    ``VECTOR_GRID_GEOMETRY``).
    """

    audit_id: str
    table_id: str
    source_page: int = Field(ge=1)
    row_idx: Optional[int] = None
    col_idx: Optional[int] = None
    original_raw_value: str
    proposed_value: str
    accepted_value: str
    inferred_candidate_only: bool
    evidence_source: str
    evidence_summary: str
    deterministic_check_passed: bool
    decision: str
    resulting_cell_status: CellQualityStatus


# ── F. PageProfile ─────────────────────────────────────────────────────────


class PageProfile(BaseModel):
    """Classification profile for a single PDF page."""

    page_number: int = Field(ge=1)
    page_type: PageType
    processing_status: PageProcessingStatus
    table_presence: TablePresenceStatus
    printable_char_count: int = Field(ge=0)
    garbled_char_ratio: float = Field(ge=0.0, le=1.0)
    image_coverage_ratio: float = Field(ge=0.0, le=1.0)
    vector_line_count: int = Field(ge=0)
    deferred_regions_count: int = Field(ge=0)


# ── G. CanonicalTable ──────────────────────────────────────────────────────


class CanonicalTable(BaseModel):
    """Shared table contract used by extraction, reconstruction,
    verification, and the pipeline.

    Contracts
    ---------
    - Field names are consistent across all modules.
    - Legitimate ragged rows are preserved, never padded.
    - Original and normalised headers are kept separate.
    - Source page information is retained per cell.
    - Duplicate rows are never silently discarded.
    - Raw source rows are not overwritten during stitching.
    """

    table_id: str
    title: Optional[str] = None
    source_pages: list[int]
    page_bbox: Optional[BoundingBox] = None
    original_headers: list[str] = Field(default_factory=list)
    normalized_headers: list[str] = Field(default_factory=list)
    header_row_count: int = Field(ge=0, default=0)
    column_types: list[DataType] = Field(default_factory=list)
    column_semantic_roles: list[str] = Field(default_factory=list)
    rows: list[list[CellRecord]] = Field(default_factory=list)
    extraction_method: str = ""
    stitch_events: list[StitchAuditEvent] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    correction_records: list[CorrectionRecord] = Field(default_factory=list)
    structural_checks_passed: bool = False
    math_validation_outcome: ValidationOutcome = ValidationOutcome.NOT_APPLICABLE
    verification_status: VerificationStatus = VerificationStatus.REVIEW_REQUIRED


# ── H. PageExtractionResult ────────────────────────────────────────────────


class PageExtractionResult(BaseModel):
    """Result of processing a single page."""

    page_number: int = Field(ge=1)
    page_profile: PageProfile
    tables: list[CanonicalTable] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    deferred_regions_count: int = Field(ge=0, default=0)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


# ── I. DocumentEvaluationReport ────────────────────────────────────────────


class DocumentEvaluationReport(BaseModel):
    """Top-level report returned by ``run_phase1_pipeline``.

    If processing fails, the pipeline returns a controlled failure
    report with ``execution_state = FAILED`` rather than raising
    an unhandled exception.  Confidential source contents are never
    exposed in failure messages.
    """

    job_id: str
    source_filename: str
    execution_state: JobExecutionState
    verification_status: VerificationStatus
    status_reason_codes: list[str] = Field(default_factory=list)
    limitation_disclaimers: list[str] = Field(default_factory=list)
    page_profiles: list[PageProfile] = Field(default_factory=list)
    page_results: list[PageExtractionResult] = Field(default_factory=list)
    canonical_tables: list[CanonicalTable] = Field(default_factory=list)
    stitch_events: list[StitchAuditEvent] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    correction_records: list[CorrectionRecord] = Field(default_factory=list)
    peak_python_heap_bytes: Optional[int] = Field(
        default=None,
        description=(
            "Peak Python heap usage in bytes via tracemalloc. "
            "Not total OS process RAM."
        ),
    )
