---
phase: 4
plan: 3
wave: 2
depends_on: [4.1, 4.2]
files_modified:
  - backend/tests/unit/test_quality_gate.py
autonomous: true
must_haves:
  truths:
    - "Table arithmetic tests verify correct totals, discrepancies, negative numbers, and subtotals."
    - "Discrepancy tests prove printed cell values are preserved and never auto-balanced."
    - "Document quality gate tests verify all 4 verification status levels."
    - "Scanned documents are proven to receive REVIEW_REQUIRED and OCR_REQUIRED_FOR_SCANNED_CONTENT."
    - "Zero-table documents are proven to receive FAILED and NO_TABLES_FOUND."
    - "Mandatory verbatim disclaimer is proven present and exact in all non-fatal evaluations."
  artifacts:
    - "backend/tests/unit/test_quality_gate.py exists"
---

# Plan 4.3: Phase 4 Unit Test Suite

## Objective
Author comprehensive unit tests in `backend/tests/unit/test_quality_gate.py` verifying table arithmetic consistency evaluation, source discrepancy preservation, ambiguous scope handling, conservative decision precedence, reason code assignment, and verbatim disclaimer attachment in accordance with MASTER_DIRECTIVE.md Sections 16 and 17 and REQ-10/REQ-11.

## Context
- `MASTER_DIRECTIVE.md` (Sections 16, 17, 20)
- `.gsd/SPEC.md` (Goal 4)
- `.gsd/REQUIREMENTS.md` (REQ-10, REQ-11, REQ-13)
- `.gsd/phases/4/RESEARCH.md`
- `backend/app/verification/quality_gate.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Author unit tests for table arithmetic consistency</name>
  <files>
    backend/tests/unit/test_quality_gate.py
  </files>
  <action>
    Create `backend/tests/unit/test_quality_gate.py` with test class `TestTableArithmeticConsistency`:
    1. Correct Total Row:
       - Table with rows [100.00, 200.00] and Total row [300.00] -> returns `ValidationOutcome.PASSED`, 0 issues.
    2. Arithmetic Discrepancy:
       - Table with rows [100.00, 200.00] and Total row [350.00] -> returns `ValidationOutcome.FAILED_VALIDATION`, 1 issue.
       - Verify issue code is `SOURCE_ARITHMETIC_DISCREPANCY`.
       - Verify `expected_value == "300.00"`, `actual_value == "350.00"`.
       - Verify cell's `raw_value` and `accepted_value` remain `"350.00"` (NOT auto-corrected to 300.00).
       - Verify total cell status is `CellQualityStatus.ANOMALY_FLAGGED`.
    3. Negative Numbers:
       - Table with rows [100.00, -40.00] and Total row [60.00] -> returns `ValidationOutcome.PASSED`.
    4. Subtotals and Grand Totals:
       - Table with subtotal rows and grand total row: verify subtotals sum preceding body rows and grand total does not double-count.
    5. No Total Row:
       - Table with only body data and no summary row -> returns `ValidationOutcome.NOT_APPLICABLE`, 0 issues.
    6. Ambiguous Calculation Scope:
       - Summary row with 0 preceding body rows -> returns `ValidationOutcome.FAILED_VALIDATION`, issue `ARITHMETIC_SCOPE_AMBIGUOUS`.
    
    AVOID: Using binary floats for test values; construct all expectations with `Decimal`.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_quality_gate.py -k TestTableArithmeticConsistency"
  </verify>
  <done>
    `TestTableArithmeticConsistency` passes 100% of test cases verifying arithmetic validation, discrepancy reporting, and value preservation.
  </done>
</task>

<task type="auto">
  <name>Author unit tests for document quality gate and conservative decision precedence</name>
  <files>
    backend/tests/unit/test_quality_gate.py
  </files>
  <action>
    In `backend/tests/unit/test_quality_gate.py`, add test class `TestDocumentQualityGate`:
    1. Fatal Execution State:
       - Report with `execution_state == JobExecutionState.FAILED` -> `VerificationStatus.FAILED`.
    2. Zero-Table Digital Document:
       - Report with all pages inspected, zero tables, `deferred_regions == 0`, all pages `CONFIRMED_ABSENT` -> `VerificationStatus.FAILED`, reason `NO_TABLES_FOUND`.
    3. Scanned-Only Document:
       - Report with scanned pages (`UNKNOWN_PENDING_OCR`) -> `VerificationStatus.REVIEW_REQUIRED`, reason `OCR_REQUIRED_FOR_SCANNED_CONTENT`.
    4. Hybrid Document with Deferred Regions:
       - Report with hybrid page and `deferred_regions_count == 2` -> `VerificationStatus.REVIEW_REQUIRED`.
    5. Unresolved Stitch Review:
       - Report with a stitch event having `StitchDecision.STITCH_REVIEW_REQUIRED` -> `VerificationStatus.REVIEW_REQUIRED`.
    6. Arithmetic Discrepancy in Document:
       - Report containing a table with `SOURCE_ARITHMETIC_DISCREPANCY` -> `VerificationStatus.REVIEW_REQUIRED`.
    7. Clean Document with No Math Checks:
       - Report with extractable tables, clean completion, but no total rows -> `VerificationStatus.VERIFIED_WITH_WARNINGS`.
    8. Fully Verified Document:
       - Clean tables, arithmetic `PASSED`, no warnings -> `VerificationStatus.VERIFIED`.
    9. Mandatory Verbatim Disclaimer:
       - In all non-fatal evaluations, verify `report.limitation_disclaimers` contains the exact verbatim text:
         `"Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."`
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_quality_gate.py"
  </verify>
  <done>
    `test_quality_gate.py` passes 100% of test cases covering all 4 verification status levels, reason codes, and the verbatim disclaimer.
  </done>
</task>

## Success Criteria
- [ ] Table arithmetic checks verify correct, incorrect, negative, and subtotal scenarios.
- [ ] `SOURCE_ARITHMETIC_DISCREPANCY` verified with source value preservation.
- [ ] All 4 `VerificationStatus` outcomes verified with synthetic report fixtures.
- [ ] Reason codes `NO_TABLES_FOUND` and `OCR_REQUIRED_FOR_SCANNED_CONTENT` validated.
- [ ] Exact verbatim disclaimer confirmed present in `limitation_disclaimers`.
- [ ] Zero unclosed file handles or warnings.
