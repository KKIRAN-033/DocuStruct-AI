---
phase: 2
plan: 4
wave: 3
depends_on: [2.1, 2.2, 2.3]
files_modified:
  - backend/tests/conftest.py
  - backend/tests/unit/test_step_1_4_page_router.py
  - backend/tests/unit/test_normalizer_integrity.py
  - backend/tests/unit/test_step_1_5_digital_extractor.py
autonomous: true
must_haves:
  truths:
    - "All page router classification states (DIGITAL, SCANNED, HYBRID, EMPTY) are covered by unit tests."
    - "Normalizer tests verify Indian/standard grouping, all negative formats, identifier leading zeros, and Decimal exactness."
    - "Normalizer tests verify formula-risk detection on =, +, -, @, \\t, \\r while proving numeric negatives do not trigger formula risk."
    - "Digital extractor tests verify line-based extraction and borderless fallback on synthetic PDFs."
    - "Zero unclosed file handles on Windows during test execution."
  artifacts:
    - "backend/tests/unit/test_step_1_4_page_router.py exists"
    - "backend/tests/unit/test_normalizer_integrity.py exists"
    - "backend/tests/unit/test_step_1_5_digital_extractor.py exists"
---

# Plan 2.4: Phase 2 Unit Test Suite

## Objective
Author comprehensive unit tests and synthetic PDF fixtures for Page Router (`test_step_1_4_page_router.py`), Normalizer (`test_normalizer_integrity.py`), and Digital Table Extractor (`test_step_1_5_digital_extractor.py`), verifying real behavior across all edge cases in accordance with MASTER_DIRECTIVE.md Sections 11, 12, 13, and 20.

## Context
- `MASTER_DIRECTIVE.md` (Sections 11, 12, 13, 19, 20)
- `.gsd/SPEC.md` (Goals 1, 2, 6)
- `.gsd/REQUIREMENTS.md` (REQ-05, REQ-06, REQ-07, REQ-13, REQ-14)
- `.gsd/phases/2/RESEARCH.md`
- `backend/app/ingestion/page_router.py`
- `backend/app/extraction/normalizer.py`
- `backend/app/extraction/digital_extractor.py`

## Tasks

<task type="auto">
  <name>Author synthetic PDF fixtures and Page Router unit tests</name>
  <files>
    backend/tests/conftest.py
    backend/tests/unit/test_step_1_4_page_router.py
  </files>
  <action>
    1. Update `backend/tests/conftest.py` with synthetic PDF fixtures generated via PyMuPDF:
       - `synthetic_scanned_pdf`: 1-page PDF containing an embedded image occupying >60% of page area and 0 printable text.
       - `synthetic_hybrid_pdf`: 1-page PDF containing printable text (>=50 chars) and an embedded image occupying ~25% of page area.
       - `synthetic_empty_page_pdf`: 1-page PDF with no text, no images, and no drawings.
       - `synthetic_nontable_pdf`: 1-page digital PDF with sentences and paragraphs but no tables or aligned columns.
       - `synthetic_ruled_table_pdf`: 1-page digital PDF with drawn grid lines (`draw_line`) and cell text in grid intersections.
       - `synthetic_borderless_table_pdf`: 1-page digital PDF with coordinate-aligned columns and rows but zero vector lines.
    2. Create `backend/tests/unit/test_step_1_4_page_router.py`:
       - `TestPageSignalAnalysis`: verify printable char count, garbled char ratio, image coverage ratio, vector line count.
       - `TestPageClassification`:
         * Verify digital page classified as `PageType.DIGITAL`, `PageProcessingStatus.EXTRACTED`.
         * Verify scanned page classified as `PageType.SCANNED`, `PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR`, `TablePresenceStatus.UNKNOWN_PENDING_OCR`.
         * Verify hybrid page classified as `PageType.HYBRID`, `deferred_regions_count >= 1`.
         * Verify blank page classified as `PageType.EMPTY_OR_UNREADABLE`, `PageProcessingStatus.EMPTY_PAGE`, `TablePresenceStatus.CONFIRMED_ABSENT`.
       - `TestResourceDiscipline`: verify document handle closed after calling `route_document_pages`.

    AVOID: Mocking PyMuPDF or pdfplumber in tests; all tests must execute against real synthetic PDFs generated in `conftest.py`.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_step_1_4_page_router.py"
  </verify>
  <done>
    `test_step_1_4_page_router.py` passes 100% of test cases verifying all page classification states, explainable signals, and resource cleanup.
  </done>
</task>

<task type="auto">
  <name>Author Normalizer and Digital Extractor unit tests</name>
  <files>
    backend/tests/unit/test_normalizer_integrity.py
    backend/tests/unit/test_step_1_5_digital_extractor.py
  </files>
  <action>
    1. Create `backend/tests/unit/test_normalizer_integrity.py`:
       - `TestNumericNormalization`:
         * Standard grouping: `"1,234,567.89"` -> `Decimal("1234567.89")`.
         * Indian grouping: `"12,34,567.89"` -> `Decimal("1234567.89")`.
         * Leading minus: `"-450.50"` -> `Decimal("-450.50")`.
         * Trailing minus: `"450.50-"` -> `Decimal("-450.50")`.
         * Accounting parentheses: `"(450.50)"` -> `Decimal("-450.50")`.
         * High precision: `"0.0001234567"` -> `DataType.HIGH_PRECISION_DECIMAL`.
         * Malformed grouping: `"12,345,67.89"` -> not parsed as valid numeric; returns raw string without comma stripping.
       - `TestIdentifierPreservation`:
         * Leading zeros: `"0012345"` under header `"Account"` preserves `"0012345"` as `DataType.IDENTIFIER`.
       - `TestFormulaRiskBoundary`:
         * Formula prefixes on strings: `"=SUM(A1)"`, `"+123"`, `"-TEXT"`, `"@CMD"`, `"\tTEST"`, `"\rTEST"` -> `formula_risk_detected == True`.
         * Valid numeric negatives: `"-450.50"`, `"(450.50)"`, `"450.50-"` -> `formula_risk_detected == False`.
         * Verify raw value is never prepended with apostrophe or mutated.
       - `TestImmutabilityAndDecimalSafety`:
         * Verify `raw_value` is never modified.
         * Verify `numeric_decimal` is constructed via `Decimal(str)` without binary float precision loss.
    2. Create `backend/tests/unit/test_step_1_5_digital_extractor.py`:
       - `TestRuledTableExtraction`:
         * Extract table from `synthetic_ruled_table_pdf`: verify `extraction_method == "LINE_BASED_RULING"`, row count, col count, cell `bbox` exactness.
       - `TestBorderlessTableExtraction`:
         * Extract table from `synthetic_borderless_table_pdf`: verify `extraction_method == "COORDINATE_INTERVAL_FALLBACK"`, `coord_exact == False`.
       - `TestEdgeCasesAndPreservation`:
         * Non-table digital page returns 0 tables.
         * Duplicate rows are preserved, never discarded.
         * Ragged rows preserved without artificial truncation or padding.
       - `TestHandleClosure`:
         * Verify `pdfplumber.PDF` handle is closed even when an exception is simulated during extraction.

    AVOID: Asserting `assert True` or tautological checks; every test must verify concrete numeric, string, or boolean values.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_normalizer_integrity.py backend/tests/unit/test_step_1_5_digital_extractor.py"
  </verify>
  <done>
    `test_normalizer_integrity.py` and `test_step_1_5_digital_extractor.py` pass 100% of test cases with meaningful assertions and zero unclosed file handles on Windows.
  </done>
</task>

## Success Criteria
- [ ] Synthetic PDF fixtures in `conftest.py` cover ruled, borderless, scanned, hybrid, and non-table pages.
- [ ] `test_step_1_4_page_router.py` verifies all 4 page classification types.
- [ ] `test_normalizer_integrity.py` verifies Indian/standard grouping, negatives, identifier leading zeros, and formula-risk detection.
- [ ] Valid numeric negatives proven not to trigger formula risk.
- [ ] `test_step_1_5_digital_extractor.py` verifies ruled extraction and coordinate fallback.
- [ ] All tests pass without warnings or unclosed Windows file handles.
