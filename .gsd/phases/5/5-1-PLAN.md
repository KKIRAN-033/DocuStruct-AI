---
phase: 5
plan: 1
wave: 1
depends_on: []
files_modified:
  - backend/app/pipeline.py
  - backend/app/__init__.py
autonomous: true
must_haves:
  truths:
    - "run_phase1_pipeline executes the full 19-step processing sequence."
    - "PyMuPDF and pdfplumber document handles are guaranteed closed."
    - "Isolated workspaces are cleaned up without deleting the original user PDF."
    - "Operational security and ingestion errors return controlled failure reports with execution_state=FAILED."
    - "Peak Python heap bytes are recorded when tracemalloc is enabled."
  artifacts:
    - "backend/app/pipeline.py exists and exports run_phase1_pipeline"
    - "backend/app/__init__.py exports run_phase1_pipeline"
---

# Plan 5.1: End-to-End Pipeline Coordinator

## Objective
Implement `run_phase1_pipeline` in `backend/app/pipeline.py` coordinating the complete Phase 1 ingestion, routing, extraction, normalization, reconstruction, arithmetic verification, and quality gate sequence, enforcing guaranteed Windows file-handle closure, workspace cleanup, and safe error reporting in compliance with MASTER_DIRECTIVE.md Section 18 and REQ-12.

## Context
- `MASTER_DIRECTIVE.md` (Sections 18, 19)
- `.gsd/SPEC.md` (Goal 1-5)
- `.gsd/REQUIREMENTS.md` (REQ-12, REQ-13, NFR-01, NFR-02)
- `.gsd/phases/5/RESEARCH.md`
- `backend/app/config/settings.py`
- `backend/app/config/calibration.py`
- `backend/app/ingestion/security_gate.py`
- `backend/app/ingestion/page_router.py`
- `backend/app/extraction/digital_extractor.py`
- `backend/app/extraction/table_reconstructor.py`
- `backend/app/verification/quality_gate.py`
- `backend/app/models/domain.py`
- `backend/app/models/state.py`

## Tasks

<task type="auto">
  <name>Implement pipeline coordinator sequence and resource safety</name>
  <files>
    backend/app/pipeline.py
    backend/app/__init__.py
  </files>
  <action>
    Create `backend/app/pipeline.py` with `run_phase1_pipeline`:
    1. Signature:
       ```python
       def run_phase1_pipeline(
           file_path: Path,
           original_filename: Optional[str] = None,
           settings: Optional[AppSettings] = None,
           calibration: Optional[CalibrationConfig] = None,
       ) -> DocumentEvaluationReport:
       ```
    2. Initialization:
       - Resolve `settings` and `calibration` via defaults (`get_settings()`, `get_calibration()`).
       - Generate `job_id = str(uuid.uuid4())`.
       - Record start time, track memory via `tracemalloc` if `settings.enable_tracemalloc` is True.
       - Normalize `source_filename = original_filename or file_path.name`.
    3. Security Gate & Workspace:
       - Run `validate_pdf_input(file_path, settings)`.
       - Create isolated workspace via `create_job_workspace(settings.workspace_base_dir, job_id)`.
       - Enclose subsequent operations in `try ... finally` block ensuring `cleanup_job_workspace(workspace_dir, file_path)` is executed.
    4. Processing Sequence:
       - Open PDF safely with `pymupdf.open(str(file_path))` in a nested `try ... finally` block.
       - Page Routing: Iterate pages sequentially (`page_idx` from 0 to `doc.page_count - 1`), calling `route_page(doc, page_idx, settings, calibration)`. Store `PageProfile`s.
       - Close PyMuPDF doc handle explicitly before proceeding to extraction.
       - Digital Extraction: For each page with `PageType.DIGITAL` (or `HYBRID`), call `extract_digital_tables(file_path, page_num, calibration, page_profile)`. Record `PageExtractionResult` per page.
       - Table Stitching: Pass extracted tables across adjacent pages to `reconstruct_multipage_tables(extracted_tables, calibration)`. Collect canonical tables and stitch events.
       - Structural Validation: Verify table dimensions, header consistency, set `structural_checks_passed = True`.
       - Quality Gate: Call `evaluate_document_quality(report)` from `app.verification.quality_gate`.
       - Memory Measurement: Record peak Python heap bytes if tracemalloc active.
       - Return populated `DocumentEvaluationReport`.
    5. Export `run_phase1_pipeline` in `backend/app/__init__.py`.
  </action>
  <verify>
    powershell -Command "python -c 'from app.pipeline import run_phase1_pipeline; print(callable(run_phase1_pipeline))'"
  </verify>
  <done>
    `run_phase1_pipeline` coordinates all processing steps with strict try/finally resource safety.
  </done>
</task>

<task type="auto">
  <name>Implement controlled operational error handling in pipeline</name>
  <files>
    backend/app/pipeline.py
  </files>
  <action>
    In `backend/app/pipeline.py`, add controlled operational error handling:
    1. Catch `SecurityGateError` subclasses (`FileSizeExceededError`, `EncryptedPDFError`, `CorruptPDFError`, `PageCountExceededError`, `InvalidPDFSignatureError`, `PathTraversalError`, `WorkspaceIsolationError`):
       - Build and return `DocumentEvaluationReport`:
         * `job_id`: generated UUID.
         * `source_filename`: sanitized filename.
         * `execution_state`: `JobExecutionState.FAILED`.
         * `verification_status`: `VerificationStatus.FAILED`.
         * `status_reason_codes`: mapped reason code (e.g. `FILE_SIZE_EXCEEDED`, `ENCRYPTED_PDF`, `PAGE_COUNT_EXCEEDED`, `SECURITY_GATE_FAILED`).
         * `limitation_disclaimers`: `[MANDATORY_VERBATIM_DISCLAIMER]` or security diagnostic.
         * Do not expose raw file text or paths in user-facing failure messages.
    2. Catch general operational exceptions (`FileNotFoundError`, `ValueError`):
       - Return controlled `DocumentEvaluationReport` with `execution_state = JobExecutionState.FAILED` and clean diagnostics.
    3. Ensure `cleanup_job_workspace` is called in all failure scenarios without deleting the original user file.
  </action>
  <verify>
    powershell -Command "python -c 'import tempfile, pathlib; from app.pipeline import run_phase1_pipeline; r = run_phase1_pipeline(pathlib.Path(\"nonexistent.pdf\")); print(r.execution_state.value)'"
  </verify>
  <done>
    Operational errors return structured `DocumentEvaluationReport` instances with `execution_state = FAILED` instead of unhandled crashes.
  </done>
</task>

## Success Criteria
- [ ] `run_phase1_pipeline` executes the full 19-step workflow.
- [ ] Safe PyMuPDF and pdfplumber handle management enforced via try/finally.
- [ ] Temporary workspace cleaned up without touching input PDF.
- [ ] Security exceptions return controlled `FAILED` reports.
- [ ] Clean package exports in `backend/app/__init__.py`.
