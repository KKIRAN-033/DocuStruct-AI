---
phase: 5
plan: 3
wave: 2
depends_on: [5.1, 5.2]
files_modified:
  - backend/tests/unit/test_phase1_pipeline.py
autonomous: true
must_haves:
  truths:
    - "Digital PDF with table achieves COMPLETED execution state and VERIFIED status."
    - "Digital PDF with no tables achieves COMPLETED execution state and FAILED status with NO_TABLES_FOUND."
    - "Scanned PDF achieves COMPLETED execution state and REVIEW_REQUIRED with OCR_REQUIRED_FOR_SCANNED_CONTENT."
    - "Discrepancy PDF achieves COMPLETED execution state and REVIEW_REQUIRED with SOURCE_ARITHMETIC_DISCREPANCY."
    - "Corrupt and encrypted files return controlled FAILED reports."
    - "Temporary workspaces are verified deleted while input PDF remains untouched."
  artifacts:
    - "backend/tests/unit/test_phase1_pipeline.py exists and passes 100%"
---

# Plan 5.3: End-to-End Pipeline & Integration Test Suite

## Objective
Author comprehensive end-to-end pipeline integration tests in `backend/tests/unit/test_phase1_pipeline.py` verifying full-pipeline execution across digital, non-table, scanned, hybrid, discrepancy, and corrupt inputs, testing Windows file-handle cleanup and workspace lifecycle in accordance with MASTER_DIRECTIVE.md Sections 18, 19, and 20 and REQ-12/REQ-13.

## Context
- `MASTER_DIRECTIVE.md` (Sections 18, 19, 20)
- `.gsd/SPEC.md` (Goal 1-6)
- `.gsd/REQUIREMENTS.md` (REQ-12, REQ-13, REQ-14)
- `.gsd/phases/5/RESEARCH.md`
- `backend/app/pipeline.py`
- `backend/tests/conftest.py`

## Tasks

<task type="auto">
  <name>Author end-to-end pipeline execution and quality tests</name>
  <files>
    backend/tests/unit/test_phase1_pipeline.py
  </files>
  <action>
    Create `backend/tests/unit/test_phase1_pipeline.py` with test class `TestPhase1PipelineExecution`:
    1. `test_pipeline_digital_ruled_table`:
       - Runs `run_phase1_pipeline` on `synthetic_ruled_table_pdf`.
       - Asserts `execution_state == JobExecutionState.COMPLETED`.
       - Asserts `verification_status in (VerificationStatus.VERIFIED, VerificationStatus.VERIFIED_WITH_WARNINGS)`.
       - Asserts `len(report.canonical_tables) >= 1`.
       - Asserts `MANDATORY_VERBATIM_DISCLAIMER` in `report.limitation_disclaimers`.
    2. `test_pipeline_digital_no_tables`:
       - Runs on `synthetic_nontable_pdf`.
       - Asserts `execution_state == JobExecutionState.COMPLETED`.
       - Asserts `verification_status == VerificationStatus.FAILED`.
       - Asserts `REASON_NO_TABLES_FOUND` in `report.status_reason_codes`.
    3. `test_pipeline_scanned_pdf`:
       - Runs on `synthetic_scanned_pdf`.
       - Asserts `execution_state == JobExecutionState.COMPLETED`.
       - Asserts `verification_status == VerificationStatus.REVIEW_REQUIRED`.
       - Asserts `REASON_OCR_REQUIRED_FOR_SCANNED` in `report.status_reason_codes`.
    4. `test_pipeline_hybrid_pdf`:
       - Runs on `synthetic_hybrid_pdf`.
       - Asserts `execution_state == JobExecutionState.COMPLETED`.
       - Asserts `verification_status == VerificationStatus.REVIEW_REQUIRED`.
       - Asserts `REASON_DEFERRED_REGIONS_REMAIN` in `report.status_reason_codes`.
    5. `test_pipeline_multipage_continuation`:
       - Runs on `synthetic_multipage_continuation_pdf`.
       - Asserts `execution_state == JobExecutionState.COMPLETED`.
       - Asserts tables from page 1 and page 2 are stitched into 1 canonical table with contiguous `row_idx`.
    6. `test_pipeline_arithmetic_discrepancy`:
       - Runs on `synthetic_arithmetic_discrepancy_pdf`.
       - Asserts `verification_status == VerificationStatus.REVIEW_REQUIRED`.
       - Asserts `REASON_SOURCE_ARITHMETIC_DISCREPANCY` in `report.status_reason_codes`.
       - Asserts printed total is preserved as 350.00.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_phase1_pipeline.py -k TestPhase1PipelineExecution"
  </verify>
  <done>
    `TestPhase1PipelineExecution` validates all document classifications, routing, and extraction outcomes end-to-end.
  </done>
</task>

<task type="auto">
  <name>Author security error handling and resource lifecycle tests</name>
  <files>
    backend/tests/unit/test_phase1_pipeline.py
  </files>
  <action>
    In `backend/tests/unit/test_phase1_pipeline.py`, add test class `TestPhase1PipelineSafetyAndErrors`:
    1. `test_pipeline_corrupt_pdf_controlled_failure`:
       - Runs on `corrupt_pdf_file`.
       - Asserts `execution_state == JobExecutionState.FAILED`.
       - Asserts `verification_status == VerificationStatus.FAILED`.
       - Asserts no unhandled exception raised.
    2. `test_pipeline_encrypted_pdf_controlled_failure`:
       - Runs on `encrypted_pdf`.
       - Asserts `execution_state == JobExecutionState.FAILED` and reason code reflects encryption.
    3. `test_pipeline_nonexistent_file`:
       - Runs on non-existent path.
       - Asserts controlled `FAILED` report.
    4. `test_pipeline_workspace_cleaned_and_original_preserved`:
       - Verifies that after execution, workspace directory is cleaned up and original input PDF still exists.
    5. `test_pipeline_cleanup_on_exception`:
       - Mocks an exception during extraction and verifies workspace is still cleaned up via try/finally.
    6. `test_pipeline_heap_measurement_recorded`:
       - Runs with `enable_tracemalloc = True`.
       - Asserts `report.peak_python_heap_bytes is not None` and `> 0`.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/unit/test_phase1_pipeline.py"
  </verify>
  <done>
    `test_phase1_pipeline.py` passes 100% of integration and safety tests.
  </done>
</task>

## Success Criteria
- [ ] End-to-end pipeline tested on ruled, nontable, scanned, hybrid, and discrepancy PDFs.
- [ ] Controlled failure verified for corrupt, encrypted, and missing files.
- [ ] Windows handle safety and workspace cleanup verified under normal and error flows.
- [ ] Original user input file strictly preserved in all cases.
- [ ] Python heap memory tracking verified.
