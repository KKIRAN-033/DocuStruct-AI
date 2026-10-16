/**
 * DocuStruct AI — Frontend Domain Type Contracts
 *
 * Grounded directly in backend Pydantic models:
 *   - backend/app/models/state.py
 *   - backend/app/models/domain.py
 *   - backend/app/verification/quality_gate.py
 *
 * Design Invariants:
 *   - `raw_value` is immutable source text.
 *   - `numeric_decimal` is serialized as string to avoid IEEE 754 precision loss.
 *   - `JobExecutionState` (operational execution) is strictly decoupled from
 *     `VerificationStatus` (tabular data quality).
 */

// ── State Enumerations ────────────────────────────────────────────────────────

export type JobExecutionState =
  | 'QUEUED'
  | 'UNDERSTANDING'
  | 'EXTRACTING'
  | 'RECONSTRUCTING'
  | 'VERIFYING'
  | 'DIAGNOSING'
  | 'CORRECTING'
  | 'REVALIDATING'
  | 'DELIVERING'
  | 'COMPLETED'
  | 'FAILED';

export type VerificationStatus =
  | 'VERIFIED'
  | 'VERIFIED_WITH_WARNINGS'
  | 'REVIEW_REQUIRED'
  | 'FAILED';

export type PageType =
  | 'DIGITAL'
  | 'SCANNED'
  | 'HYBRID'
  | 'EMPTY_OR_UNREADABLE';

export type PageProcessingStatus =
  | 'EXTRACTED'
  | 'INCOMPLETE_DEFERRED_TO_OCR'
  | 'EMPTY_PAGE'
  | 'FAILED_PAGE';

export type TablePresenceStatus =
  | 'CONFIRMED_PRESENT'
  | 'CONFIRMED_ABSENT'
  | 'UNKNOWN_PENDING_OCR';

export type ValidationOutcome =
  | 'PASSED'
  | 'PASSED_WITH_WARNINGS'
  | 'FAILED_VALIDATION'
  | 'NOT_APPLICABLE';

export type StitchDecision =
  | 'STITCH_CONFIRMED'
  | 'STITCH_REJECTED'
  | 'STITCH_REVIEW_REQUIRED';

export type CellQualityStatus =
  | 'EXTRACTED_AS_IS'
  | 'CORROBORATED'
  | 'CORRECTED_WITH_EVIDENCE'
  | 'LOW_CONFIDENCE_WARNING'
  | 'ANOMALY_FLAGGED'
  | 'ILLEGIBLE_OR_MISSING';

export type DataType =
  | 'STRING'
  | 'IDENTIFIER'
  | 'INTEGER'
  | 'DECIMAL'
  | 'HIGH_PRECISION_DECIMAL'
  | 'DATE'
  | 'EMPTY';

// ── Standard Constants & Reason Codes ─────────────────────────────────────────

export const MANDATORY_VERBATIM_DISCLAIMER =
  'Structural integrity and internal arithmetic consistency were verified. ' +
  'This does not independently prove every source cell is correct and cannot ' +
  'rule out offsetting cell errors or errors in non-numeric text.';

export const REASON_NO_TABLES_FOUND = 'NO_TABLES_FOUND';
export const REASON_OCR_REQUIRED_FOR_SCANNED = 'OCR_REQUIRED_FOR_SCANNED_CONTENT';
export const REASON_DEFERRED_REGIONS_REMAIN = 'DEFERRED_REGIONS_REMAIN';
export const REASON_SOURCE_ARITHMETIC_DISCREPANCY = 'SOURCE_ARITHMETIC_DISCREPANCY';
export const REASON_ARITHMETIC_SCOPE_AMBIGUOUS = 'ARITHMETIC_SCOPE_AMBIGUOUS';
export const REASON_STITCH_REVIEW_REQUIRED = 'STITCH_REVIEW_REQUIRED';
export const REASON_STRUCTURAL_CHECKS_FAILED = 'STRUCTURAL_CHECKS_FAILED';
export const REASON_EXECUTION_FAILED = 'EXECUTION_FAILED';

// ── Domain Model Contracts ───────────────────────────────────────────────────

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  page_width: number;
  page_height: number;
  coord_exact: boolean;
  norm_x0: number;
  norm_x1: number;
  norm_y0: number;
  norm_y1: number;
}

export interface CellRecord {
  table_id: string;
  row_idx: number;
  col_idx: number;
  source_page: number;
  bbox: BoundingBox | null;
  extraction_method: string;
  ocr_confidence: number | null;
  raw_value: string;
  normalized_value: string | null;
  numeric_decimal: string | null;
  accepted_value: string;
  inferred_candidate_value: string | null;
  data_type: DataType;
  quality_status: CellQualityStatus;
  formula_risk_detected: boolean;
  notes: string[];
}

export interface StitchAuditEvent {
  upper_table_id: string;
  lower_table_id: string;
  upper_page: number;
  lower_page: number;
  decision: StitchDecision;
  header_similarity_score: number;
  col_overlap_ratio: number;
  type_compatibility_ratio: number;
  repeated_header_rows_stripped: number;
  reasons: string[];
}

export interface ValidationIssue {
  issue_id: string;
  table_id: string;
  source_page: number;
  row_idx: number | null;
  col_idx: number | null;
  issue_code: string;
  severity: string;
  description: string;
  expected_value: string | null;
  actual_value: string | null;
  resolved: boolean;
}

export interface CorrectionRecord {
  audit_id: string;
  table_id: string;
  source_page: number;
  row_idx: number | null;
  col_idx: number | null;
  original_raw_value: string;
  proposed_value: string;
  accepted_value: string;
  inferred_candidate_only: boolean;
  evidence_source: string;
  evidence_summary: string;
  deterministic_check_passed: boolean;
  decision: string;
  resulting_cell_status: CellQualityStatus;
}

export interface PageProfile {
  page_number: number;
  page_type: PageType;
  processing_status: PageProcessingStatus;
  table_presence: TablePresenceStatus;
  printable_char_count: number;
  garbled_char_ratio: number;
  image_coverage_ratio: number;
  vector_line_count: number;
  deferred_regions_count: number;
}

export interface CanonicalTable {
  table_id: string;
  title: string | null;
  source_pages: number[];
  page_bbox: BoundingBox | null;
  original_headers: string[];
  normalized_headers: string[];
  header_row_count: number;
  column_types: DataType[];
  column_semantic_roles: string[];
  rows: CellRecord[][];
  extraction_method: string;
  stitch_events: StitchAuditEvent[];
  validation_issues: ValidationIssue[];
  correction_records: CorrectionRecord[];
  structural_checks_passed: boolean;
  math_validation_outcome: ValidationOutcome;
  verification_status: VerificationStatus;
}

export interface PageExtractionResult {
  page_number: number;
  page_profile: PageProfile;
  tables: CanonicalTable[];
  issues: ValidationIssue[];
  deferred_regions_count: number;
  diagnostics: Record<string, unknown>;
}

export interface DocumentEvaluationReport {
  job_id: string;
  source_filename: string;
  execution_state: JobExecutionState;
  verification_status: VerificationStatus;
  status_reason_codes: string[];
  limitation_disclaimers: string[];
  page_profiles: PageProfile[];
  page_results: PageExtractionResult[];
  canonical_tables: CanonicalTable[];
  stitch_events: StitchAuditEvent[];
  validation_issues: ValidationIssue[];
  correction_records: CorrectionRecord[];
  peak_python_heap_bytes: number | null;
}
