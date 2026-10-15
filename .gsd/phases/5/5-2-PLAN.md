---
phase: 5
plan: 2
wave: 1
depends_on: []
files_modified:
  - backend/tests/conftest.py
  - backend/tests/evaluation/__init__.py
  - backend/tests/evaluation/regression_harness.py
autonomous: true
must_haves:
  truths:
    - "conftest.py provides synthetic fixtures for multipage continuation, duplicate rows, and arithmetic discrepancies."
    - "regression_harness.py defines structured evaluation case schemas and runner logic."
    - "regression_harness.py strictly reports UNMEASURED for real-world accuracy when no manual ground truth corpus exists."
    - "Harness is executable via CLI with documented commands."
  artifacts:
    - "backend/tests/evaluation/regression_harness.py exists and is runnable"
    - "backend/tests/conftest.py includes complete fixture suite"
---

# Plan 5.2: Comprehensive Synthetic Fixtures & Evaluation Harness

## Objective
Extend synthetic PDF test fixtures in `backend/tests/conftest.py` and implement the standalone ground-truth regression evaluation harness in `backend/tests/evaluation/regression_harness.py`, strictly reporting `UNMEASURED` for unverified corpora in compliance with MASTER_DIRECTIVE.md Sections 20 and 21 and REQ-14/REQ-15/NFR-04.

## Context
- `MASTER_DIRECTIVE.md` (Sections 20, 21)
- `.gsd/SPEC.md` (Goal 6)
- `.gsd/REQUIREMENTS.md` (REQ-14, REQ-15, NFR-04)
- `.gsd/phases/5/RESEARCH.md`
- `backend/tests/conftest.py`
- `backend/app/pipeline.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Extend synthetic PDF fixtures in conftest.py</name>
  <files>
    backend/tests/conftest.py
  </files>
  <action>
    In `backend/tests/conftest.py`, add the remaining synthetic PDF fixtures specified by Section 20:
    1. `synthetic_multipage_continuation_pdf(tmp_path)`:
       - 2-page PDF.
       - Page 1: Header `["Item", "Quantity", "Amount"]` + 3 body rows.
       - Page 2: Same header repeated + 3 body rows + Total row `["Total", "6", "600.00"]`.
       - Drawn with identical horizontal grid lines and column intervals.
    2. `synthetic_duplicate_rows_pdf(tmp_path)`:
       - 1-page PDF.
       - Table with identical transaction rows (e.g. `["REF-101", "Service Fee", "15.00"]` twice).
       - Used to empirically test duplicate transaction row preservation.
    3. `synthetic_arithmetic_discrepancy_pdf(tmp_path)`:
       - 1-page PDF with ruled table:
         * Rows: `["Alpha", "100.00"]`, `["Beta", "200.00"]`.
         * Total row: `["Total", "350.00"]`.
         * Used to test end-to-end `SOURCE_ARITHMETIC_DISCREPANCY` reporting.
  </action>
  <verify>
    powershell -Command "pytest -v backend/tests/test_conftest_fixtures.py --collect-only" (or verify pytest collects conftest without errors)
  </verify>
  <done>
    `conftest.py` provides reproducible synthetic PDF fixtures for all specified layouts.
  </done>
</task>

<task type="auto">
  <name>Implement standalone regression evaluation harness</name>
  <files>
    backend/tests/evaluation/__init__.py
    backend/tests/evaluation/regression_harness.py
  </files>
  <action>
    Create `backend/tests/evaluation/regression_harness.py`:
    1. Data Models:
       - `EvaluationCase(case_id, pdf_path, expected_table_count, expected_row_counts, expected_col_counts, expected_cell_values, expected_verification_status, expected_reasons, is_synthetic)`.
       - `CaseResult(case_id, passed, table_count_match, row_count_match, col_count_match, cell_values_match, status_match, mismatches)`.
       - `EvaluationSummary(total_cases, passed_cases, failed_cases, real_world_accuracy, synthetic_fixture_accuracy)`.
    2. Runner Logic:
       - `run_case(case: EvaluationCase, settings, calibration) -> CaseResult`:
         * Invokes `run_phase1_pipeline(case.pdf_path, settings=settings, calibration=calibration)`.
         * Compares actual tables against expected table count, dimensions, cell values, and status.
         * Records detailed diagnostic mismatches.
       - `run_evaluation(cases: list[EvaluationCase]) -> EvaluationSummary`:
         * Iterates cases sequentially.
         * Computes pass/fail counts.
         * Enforces NFR-04: If cases are synthetic or no manual ground-truth corpus is configured, set `real_world_accuracy = "UNMEASURED"`.
    3. CLI Interface:
       - Implement `main()` with `argparse`:
         * `--cases-dir`: path to evaluation cases directory.
         * `--output-json`: path to write JSON evaluation summary.
         * Prints clean human-readable summary table.
  </action>
  <verify>
    powershell -Command "python -m tests.evaluation.regression_harness --help"
  </verify>
  <done>
    `regression_harness.py` provides an auditable evaluation runner that correctly marks uncalibrated metrics as `UNMEASURED`.
  </done>
</task>

## Success Criteria
- [ ] Synthetic fixtures created for multipage continuation, duplicate rows, and discrepancies.
- [ ] `regression_harness.py` implements structured case schema and evaluation logic.
- [ ] `UNMEASURED` strictly reported for real-world metrics when using synthetic cases.
- [ ] Harness executes cleanly from command line.
