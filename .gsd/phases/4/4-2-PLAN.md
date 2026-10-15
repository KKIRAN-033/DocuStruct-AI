---
phase: 4
plan: 2
wave: 1
depends_on: []
files_modified:
  - backend/app/verification/quality_gate.py
  - backend/app/verification/__init__.py
autonomous: true
must_haves:
  truths:
    - "Document quality gate evaluates verification status following conservative decision precedence."
    - "Execution failure strictly yields FAILED."
    - "Scanned content yields REVIEW_REQUIRED with OCR_REQUIRED_FOR_SCANNED_CONTENT, never CONFIRMED_ABSENT."
    - "Zero-table digital documents yield FAILED with reason NO_TABLES_FOUND only after full page inspection."
    - "Mandatory verbatim disclaimer is attached without modification or paraphrase."
  artifacts:
    - "backend/app/verification/quality_gate.py exports evaluate_document_quality"
    - "backend/app/verification/__init__.py exports MANDATORY_VERBATIM_DISCLAIMER"
---

# Plan 4.2: Document Quality Gate & Conservative Decision Precedence

## Objective
Implement `evaluate_document_quality` in `backend/app/verification/quality_gate.py` to evaluate overall document verification status (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`) based on conservative decision precedence, emit standard reason codes (`NO_TABLES_FOUND`, `OCR_REQUIRED_FOR_SCANNED_CONTENT`), and attach the mandatory verbatim disclaimer in compliance with MASTER_DIRECTIVE.md Section 17 and REQ-11.

## Context
- `MASTER_DIRECTIVE.md` (Section 17)
- `.gsd/SPEC.md` (Goal 4)
- `.gsd/REQUIREMENTS.md` (REQ-11, REQ-13)
- `.gsd/phases/4/RESEARCH.md`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Implement conservative decision precedence order</name>
  <files>
    backend/app/verification/quality_gate.py
    backend/app/verification/__init__.py
  </files>
  <action>
    In `backend/app/verification/quality_gate.py`, define reason code constants and evaluation logic:
    1. Define reason codes:
       - `REASON_NO_TABLES_FOUND = "NO_TABLES_FOUND"`
       - `REASON_OCR_REQUIRED_FOR_SCANNED = "OCR_REQUIRED_FOR_SCANNED_CONTENT"`
       - `REASON_DEFERRED_REGIONS_REMAIN = "DEFERRED_REGIONS_REMAIN"`
       - `REASON_SOURCE_ARITHMETIC_DISCREPANCY = "SOURCE_ARITHMETIC_DISCREPANCY"`
       - `REASON_ARITHMETIC_SCOPE_AMBIGUOUS = "ARITHMETIC_SCOPE_AMBIGUOUS"`
       - `REASON_STITCH_REVIEW_REQUIRED = "STITCH_REVIEW_REQUIRED"`
    2. Define mandatory verbatim disclaimer:
       `MANDATORY_VERBATIM_DISCLAIMER = "Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."`
    3. `evaluate_document_verification_status(report: DocumentEvaluationReport) -> tuple[VerificationStatus, list[str], list[str]]`:
       - Follow conservative decision order:
         * Step 1 (Fatal Execution): If `report.execution_state == JobExecutionState.FAILED` -> return `(VerificationStatus.FAILED, ["EXECUTION_FAILED"], [])`.
         * Step 2 (Zero-Table Digital): If all pages inspected, total tables == 0, `deferred_regions_count == 0`, and all pages are `CONFIRMED_ABSENT` -> return `(VerificationStatus.FAILED, [REASON_NO_TABLES_FOUND], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 3 (Scanned Content): If any page is `PageType.SCANNED` or `PageProcessingStatus.INCOMPLETE_DEFERRED_TO_OCR` -> return `(VerificationStatus.REVIEW_REQUIRED, [REASON_OCR_REQUIRED_FOR_SCANNED], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 4 (Deferred Regions): If any hybrid page has `deferred_regions_count > 0` -> return `(VerificationStatus.REVIEW_REQUIRED, [REASON_DEFERRED_REGIONS_REMAIN], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 5 (Unresolved Stitches): If any `StitchAuditEvent.decision == StitchDecision.STITCH_REVIEW_REQUIRED` -> return `(VerificationStatus.REVIEW_REQUIRED, [REASON_STITCH_REVIEW_REQUIRED], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 6 (Arithmetic Discrepancies & Ambiguities): If any issue has `SOURCE_ARITHMETIC_DISCREPANCY` or `ARITHMETIC_SCOPE_AMBIGUOUS` or table outcome is `FAILED_VALIDATION` -> return `(VerificationStatus.REVIEW_REQUIRED, [REASON_SOURCE_ARITHMETIC_DISCREPANCY], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 7 (Structural Check Failures): If any table has `structural_checks_passed == False` -> return `(VerificationStatus.REVIEW_REQUIRED, ["STRUCTURAL_CHECKS_FAILED"], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 8 (Warnings & Audited Corrections): If processing completed cleanly, but an evidence-backed correction was applied (`CORRECTED_WITH_EVIDENCE`), high-precision decimals exist, or arithmetic validation is `NOT_APPLICABLE` -> return `(VerificationStatus.VERIFIED_WITH_WARNINGS, [], [MANDATORY_VERBATIM_DISCLAIMER])`.
         * Step 9 (Verified): If all pages inspected, no deferred regions, no anomalies, applicable math is `PASSED` -> return `(VerificationStatus.VERIFIED, [], [MANDATORY_VERBATIM_DISCLAIMER])`.
  </action>
  <verify>
    powershell -Command "python -c 'from app.verification.quality_gate import MANDATORY_VERBATIM_DISCLAIMER, evaluate_document_verification_status; print(len(MANDATORY_VERBATIM_DISCLAIMER) > 0)'"
  </verify>
  <done>
    `evaluate_document_verification_status` correctly enforces conservative decision precedence and attaches reason codes and disclaimers.
  </done>
</task>

<task type="auto">
  <name>Implement document quality gate coordinator</name>
  <files>
    backend/app/verification/quality_gate.py
    backend/app/verification/__init__.py
  </files>
  <action>
    In `backend/app/verification/quality_gate.py`, implement:
    1. `evaluate_document_quality(report: DocumentEvaluationReport) -> DocumentEvaluationReport`:
       - First run arithmetic validation across all tables in `report.canonical_tables`:
         * For each table: call `evaluate_table_arithmetic_consistency(table)`.
         * Collect new validation issues into `report.validation_issues`.
       - Call `evaluate_document_verification_status(report)`.
       - Update `report.verification_status`.
       - Update `report.status_reason_codes` (merge new reasons without duplicates).
       - Ensure `MANDATORY_VERBATIM_DISCLAIMER` is appended to `report.limitation_disclaimers` if not already present.
       - Return updated `report`.
    2. Export `evaluate_document_quality`, `evaluate_document_verification_status`, and constants in `backend/app/verification/__init__.py`.
  </action>
  <verify>
    powershell -Command "python -c 'from app.verification.quality_gate import evaluate_document_quality; print(callable(evaluate_document_quality))'"
  </verify>
  <done>
    `evaluate_document_quality` runs table arithmetic evaluations and determines full-document verification status with disclaimers.
  </done>
</task>

## Success Criteria
- [ ] Conservative decision precedence order strictly applied.
- [ ] Fatal execution failure takes priority.
- [ ] Scanned pages yield `REVIEW_REQUIRED` with `OCR_REQUIRED_FOR_SCANNED_CONTENT`.
- [ ] Zero-table digital documents yield `FAILED` with `NO_TABLES_FOUND`.
- [ ] Mandatory verbatim disclaimer attached verbatim.
- [ ] Package exports clean and discoverable.
