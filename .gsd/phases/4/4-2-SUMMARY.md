# Phase 4 Plan 2 Summary: Document Quality Gate & Conservative Decision Precedence

## Implementation Details
- **Module:** `backend/app/verification/quality_gate.py`
- **Exports in:** `backend/app/verification/__init__.py`
- **Functions & Constants:**
  - `MANDATORY_VERBATIM_DISCLAIMER`: Exact required text from Section 20 of MASTER_DIRECTIVE.md:
    `"Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."`
  - Reason codes: `NO_TABLES_FOUND`, `OCR_REQUIRED_FOR_SCANNED_CONTENT`, `DEFERRED_REGIONS_REMAIN`, `SOURCE_ARITHMETIC_DISCREPANCY`, `ARITHMETIC_SCOPE_AMBIGUOUS`, `STITCH_REVIEW_REQUIRED`, `STRUCTURAL_CHECKS_FAILED`, `EXECUTION_FAILED`.
  - `evaluate_document_verification_status(report: DocumentEvaluationReport) -> tuple[VerificationStatus, list[str]]`:
    - Implements strict 9-level conservative decision precedence order:
      1. Fatal execution failure (`JobExecutionState.FAILED`) -> `FAILED` (`EXECUTION_FAILED`).
      2. Zero-table digital document (all pages `CONFIRMED_ABSENT`, 0 tables, 0 deferred regions, no scanned pages) -> `FAILED` (`NO_TABLES_FOUND`).
      3. Scanned content present -> `REVIEW_REQUIRED` (`OCR_REQUIRED_FOR_SCANNED_CONTENT`). Scanned pages are never marked `CONFIRMED_ABSENT`.
      4. Deferred regions remain -> `REVIEW_REQUIRED` (`DEFERRED_REGIONS_REMAIN`).
      5. Unresolved stitch reviews (`STITCH_REVIEW_REQUIRED`) -> `REVIEW_REQUIRED` (`STITCH_REVIEW_REQUIRED`).
      6. Arithmetic discrepancies / ambiguities -> `REVIEW_REQUIRED` (`SOURCE_ARITHMETIC_DISCREPANCY` / `ARITHMETIC_SCOPE_AMBIGUOUS`).
      7. Structural integrity check failures -> `REVIEW_REQUIRED` (`STRUCTURAL_CHECKS_FAILED`).
      8. Audited corrections applied (`CORRECTED_WITH_EVIDENCE`), high precision decimals, or math `NOT_APPLICABLE` -> `VERIFIED_WITH_WARNINGS`.
      9. Clean execution, verified math, zero anomalies -> `VERIFIED`.
  - `evaluate_document_quality(report: DocumentEvaluationReport) -> DocumentEvaluationReport`:
    - Coordinates table arithmetic consistency evaluation across all canonical tables.
    - Updates report-level verification status and appends reason codes without duplication.
    - Appends `MANDATORY_VERBATIM_DISCLAIMER` to `report.limitation_disclaimers`.

## Verification Evidence
- Unit test suite `TestDocumentQualityGate` in `test_quality_gate.py`:
  - `test_fatal_execution_state_yields_failed`: Validates priority of `JobExecutionState.FAILED`.
  - `test_zero_table_digital_document_yields_failed_no_tables_found`: Validates digital zero-table handling.
  - `test_scanned_content_yields_review_required_ocr_needed`: Validates scanned content routing to `REVIEW_REQUIRED`.
  - `test_hybrid_document_with_deferred_regions`: Validates deferred regions escalate to `REVIEW_REQUIRED`.
  - `test_unresolved_stitch_review_yields_review_required`: Validates stitch reviews block `VERIFIED`.
  - `test_arithmetic_discrepancy_in_document_yields_review_required`: Validates math errors escalate to `REVIEW_REQUIRED`.
  - `test_structural_checks_failed_yields_review_required`: Validates structural checks failure.
  - `test_clean_document_no_math_checks_yields_verified_with_warnings`: Validates math N/A downgrade to `VERIFIED_WITH_WARNINGS`.
  - `test_audited_corrections_yields_verified_with_warnings`: Validates corrections yield warnings.
  - `test_fully_verified_document`: Validates clean document yields `VERIFIED`.
  - `test_mandatory_verbatim_disclaimer_attached_verbatim`: Validates exact verbatim disclaimer string.
