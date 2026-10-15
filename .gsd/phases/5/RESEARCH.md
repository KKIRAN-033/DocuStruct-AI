# Phase 5 Research: Pipeline Integration, Evaluation Harness & Developer Experience

## Executive Summary
Phase 5 integrates all previous components (security gate, page router, normalizer, digital extractor, table reconstructor, arithmetic validator, and document quality gate) into the end-to-end pipeline entry point:
`run_phase1_pipeline(file_path: Path, original_filename: Optional[str] = None, settings: Optional[AppSettings] = None, calibration: Optional[CalibrationConfig] = None) -> DocumentEvaluationReport`

It also delivers comprehensive synthetic PDF test fixtures in `conftest.py`, the standalone ground-truth evaluation harness (`regression_harness.py`), end-to-end integration tests in `test_phase1_pipeline.py`, and developer documentation in `README.md`.

---

## 1. Pipeline Architecture & Sequence (Section 18)
The pipeline sequence executes 19 distinct steps in strict order:
1. Initialize job ID (`uuid.uuid4()`) and document metadata.
2. Load or validate `AppSettings` and `CalibrationConfig`.
3. Validate input through `validate_pdf_input(file_path, settings)`.
4. Create an isolated job workspace via `create_job_workspace(settings.workspace_base_dir, job_id)`.
5. Open and inspect the PDF using safe resource management (`try/finally` or context managers).
6. Route each page sequentially through `route_page(doc, page_num, settings, calibration)` (`max_workers = 1`).
7. Extract supported native digital tables via `extract_digital_tables`.
8. Normalize extracted cells with `normalize_cell` (preserving `raw_value`, Indian/standard formats, accounting negatives, leading zeros, and formula-risk detection).
9. Evaluate adjacent page tables for conservative multipage stitching via `reconstruct_multipage_tables`.
10. Build canonical tables (`CanonicalTable`).
11. Run structural checks (`structural_checks_passed`).
12. Run deterministic arithmetic validation via `evaluate_table_arithmetic_consistency`.
13. Collect validation issues, stitch events, and correction records.
14. Evaluate final document quality via `evaluate_document_quality`.
15. Build `DocumentEvaluationReport`.
16. Release temporary objects.
17. Close all PyMuPDF and pdfplumber document handles.
18. Clean up temporary workspaces (`cleanup_job_workspace`) while strictly preserving the original user-provided PDF file.
19. Return the final `DocumentEvaluationReport`.

---

## 2. Resource Discipline & Windows File-Handle Safety (Section 19, NFR-02)
- Windows enforces mandatory locking on open files. Deleting an isolated workspace directory while a handle is open will raise `PermissionError`.
- All `pymupdf.Document` instances must be closed inside `try ... finally` or context manager blocks before workspace cleanup is attempted.
- All `pdfplumber.open` instances must be closed inside `with` context blocks.
- The pipeline wraps execution in a top-level `try ... finally` block ensuring `cleanup_job_workspace` is always invoked regardless of whether extraction succeeds or raises an exception.
- The original input file path is never inside the job workspace and is never deleted during cleanup.

---

## 3. Error Handling Contract (Section 18)
- Operational errors (e.g. file size limit exceeded, encrypted PDF, zero pages, corrupt PDF, path traversal) must NOT crash the caller with unhandled exceptions.
- Instead, the pipeline builds and returns a valid `DocumentEvaluationReport` with:
  - `execution_state = JobExecutionState.FAILED`
  - `verification_status = VerificationStatus.FAILED`
  - `status_reason_codes = [reason_code]` (e.g. `SECURITY_GATE_FAILED`, `CORRUPT_PDF`, `ENCRYPTED_PDF`, `PAGE_COUNT_EXCEEDED`)
  - Safe diagnostic metadata without exposing sensitive document content.
- Unexpected programming errors should be logged safely and returned as controlled failure reports without masking critical traceback info in developer environments.

---

## 4. Peak Memory Tracking (Section 18, NFR-01)
- When `settings.enable_tracemalloc` is True, the pipeline measures peak Python heap usage via `tracemalloc.get_traced_memory()[1]` and assigns it to `report.peak_python_heap_bytes`.
- The documentation explicitly notes that Python heap memory is distinct from total operating system process RAM (which includes native C-libraries from PyMuPDF and pdfplumber).

---

## 5. Regression Evaluation Harness & Ground-Truth Discipline (Section 21, NFR-04)
- Implemented in `backend/tests/evaluation/regression_harness.py`.
- Evaluates:
  - Expected vs. extracted table count.
  - Expected vs. extracted row/column structure.
  - Expected vs. extracted cell values.
  - Page attribution.
  - Stitch decisions.
  - Quality gate decisions.
- **Audit Integrity Non-Negotiable (NFR-04):**
  - If no manually verified ground-truth reference dataset is provided, the harness MUST report:
    `UNMEASURED`
    for real-world accuracy metrics.
  - Synthetic test fixtures must never be falsely reported as real-world benchmark accuracy.

---

## 6. Root README & Developer Experience (Section 22)
The root `README.md` must cover:
- Architecture, mission, and Phase 1 scope.
- Explicitly mark future features (OCR, LLMs, FastAPI, Web UI) as unbuilt.
- Windows setup instructions with PowerShell commands.
- Execution states (`JobExecutionState`) vs Verification status (`VerificationStatus`).
- Mandatory verbatim disclaimer explanation.
- Normalization vs correction differences.
- Running unit tests (`pytest -v backend/tests`).
- Running the regression evaluation harness.
- Documenting that uncalibrated metrics remain `UNMEASURED`.
