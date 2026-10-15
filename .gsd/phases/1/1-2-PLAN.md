---
phase: 1
plan: 2
wave: 1
depends_on: []
---

# Plan 1.2: State Enumerations & Pydantic v2 Domain Models

## Objective
Implement typed state enumerations (`state.py`) and validated Pydantic v2 domain models (`domain.py`) with strict adherence to data contracts, immutable `raw_value`, exact Decimal arithmetic, and full JSON serialization.

## Context
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-02, REQ-03, CON-03, CON-04)
- `MASTER_DIRECTIVE.md` (Sections 8, 9)
- `.gsd/phases/1/RESEARCH.md`

## Tasks

<task type="auto">
  <name>Implement state enumerations</name>
  <files>
    backend/app/models/state.py
    backend/app/models/__init__.py
  </files>
  <action>
    Create backend/app/models/state.py with the 9 string-backed enums (inheriting from str, Enum):
    1. JobExecutionState: QUEUED, UNDERSTANDING, EXTRACTING, RECONSTRUCTING, VERIFYING, DIAGNOSING, CORRECTING, REVALIDATING, DELIVERING, COMPLETED, FAILED
    2. VerificationStatus: VERIFIED, VERIFIED_WITH_WARNINGS, REVIEW_REQUIRED, FAILED
    3. PageType: DIGITAL, SCANNED, HYBRID, EMPTY_OR_UNREADABLE
    4. PageProcessingStatus: EXTRACTED, INCOMPLETE_DEFERRED_TO_OCR, EMPTY_PAGE, FAILED_PAGE
    5. TablePresenceStatus: CONFIRMED_PRESENT, CONFIRMED_ABSENT, UNKNOWN_PENDING_OCR
    6. ValidationOutcome: PASSED, PASSED_WITH_WARNINGS, FAILED_VALIDATION, NOT_APPLICABLE
    7. StitchDecision: STITCH_CONFIRMED, STITCH_REJECTED, STITCH_REVIEW_REQUIRED
    8. CellQualityStatus: EXTRACTED_AS_IS, CORROBORATED, CORRECTED_WITH_EVIDENCE, LOW_CONFIDENCE_WARNING, ANOMALY_FLAGGED, ILLEGIBLE_OR_MISSING
    9. DataType: STRING, IDENTIFIER, INTEGER, DECIMAL, HIGH_PRECISION_DECIMAL, DATE, EMPTY

    Keep execution state strictly distinct from verification status.
    Ensure models/__init__.py exports all state enums cleanly.
  </action>
  <verify>
    powershell -Command "python -c 'from app.models.state import JobExecutionState, VerificationStatus; print(JobExecutionState.COMPLETED.value, VerificationStatus.VERIFIED.value)'"
  </verify>
  <done>
    All 9 state enums defined with exact string representations matching MASTER_DIRECTIVE.md Section 8; JSON serializable.
  </done>
</task>

<task type="auto">
  <name>Implement Pydantic v2 domain models and serialization contracts</name>
  <files>
    backend/app/models/domain.py
    backend/app/models/__init__.py
  </files>
  <action>
    Create backend/app/models/domain.py implementing validated Pydantic v2 models:
    - BoundingBox: x0, y0, x1, y1, page_width, page_height, coord_exact: bool. Validator ensuring x0 <= x1, y0 <= y1, dimensions > 0. Computed properties norm_x0, norm_x1, norm_y0, norm_y1.
    - CellRecord: table_id: str, row_idx: int, col_idx: int, source_page: int, bbox: Optional[BoundingBox], extraction_method: str, ocr_confidence: Optional[float] = None, raw_value: str, normalized_value: Optional[str] = None, numeric_decimal: Optional[Decimal] = None, accepted_value: str, inferred_candidate_value: Optional[str] = None, data_type: DataType, quality_status: CellQualityStatus, formula_risk_detected: bool = False, notes: list[str] = Field(default_factory=list).
      * Critical contract: raw_value must be immutable. Decimal values must not be converted through binary float.
    - StitchAuditEvent: upper_table_id, lower_table_id, upper_page, lower_page, decision: StitchDecision, header_similarity_score: float, col_overlap_ratio: float, type_compatibility_ratio: float, repeated_header_rows_stripped: int, reasons: list[str].
    - ValidationIssue: issue_id, table_id, source_page, row_idx: Optional[int], col_idx: Optional[int], issue_code: str, severity: str, description: str, expected_value: Optional[str] = None, actual_value: Optional[str] = None, resolved: bool = False.
    - CorrectionRecord: audit_id, table_id, source_page, row_idx: Optional[int], col_idx: Optional[int], original_raw_value: str, proposed_value: str, accepted_value: str, inferred_candidate_only: bool, evidence_source: str, evidence_summary: str, deterministic_check_passed: bool, decision: str, resulting_cell_status: CellQualityStatus.
    - PageProfile: page_number: int, page_type: PageType, processing_status: PageProcessingStatus, table_presence: TablePresenceStatus, printable_char_count: int, garbled_char_ratio: float, image_coverage_ratio: float, vector_line_count: int, deferred_regions_count: int.
    - CanonicalTable: table_id: str, title: Optional[str], source_pages: list[int], page_bbox: Optional[BoundingBox], original_headers: list[str], normalized_headers: list[str], header_row_count: int, column_types: list[DataType], column_semantic_roles: list[str], rows: list[list[CellRecord]], extraction_method: str, stitch_events: list[StitchAuditEvent], validation_issues: list[ValidationIssue], correction_records: list[CorrectionRecord], structural_checks_passed: bool, math_validation_outcome: ValidationOutcome, verification_status: VerificationStatus.
    - PageExtractionResult: page_number: int, page_profile: PageProfile, tables: list[CanonicalTable], issues: list[ValidationIssue], deferred_regions_count: int, diagnostics: dict.
    - DocumentEvaluationReport: job_id: str, source_filename: str, execution_state: JobExecutionState, verification_status: VerificationStatus, status_reason_codes: list[str], limitation_disclaimers: list[str], page_profiles: list[PageProfile], page_results: list[PageExtractionResult], canonical_tables: list[CanonicalTable], stitch_events: list[StitchAuditEvent], validation_issues: list[ValidationIssue], correction_records: list[CorrectionRecord], peak_python_heap_bytes: Optional[int] = None.

    Rebuild model schemas to resolve forward references cleanly.
    Export all models in app/models/__init__.py.
  </action>
  <verify>
    powershell -Command "python -c 'from app.models.domain import BoundingBox, CellRecord, DocumentEvaluationReport; from decimal import Decimal; b = BoundingBox(x0=10, y0=20, x1=50, y1=60, page_width=100, page_height=200, coord_exact=True); print(b.norm_x0, b.norm_y1)'"
  </verify>
  <done>
    All domain models instantiated and serialized without validation errors; Decimal exactness preserved without float conversion; BoundingBox coordinate normalization functioning.
  </done>
</task>

## Success Criteria
- [ ] 9 state enums defined in `state.py` with explicit string values.
- [ ] 9 domain models defined in `domain.py` with field validation, Decimal safety, and immutable `raw_value`.
- [ ] No circular imports; full JSON serialization verified.
