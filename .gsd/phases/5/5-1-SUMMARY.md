# Phase 5 Plan 1 Summary: End-to-End Pipeline Coordinator

## Implementation Details
- **Module:** `backend/app/pipeline.py`
- **Exported from:** `backend/app/__init__.py`
- **Key Function:**
  - `run_phase1_pipeline(file_path: Path, original_filename: Optional[str] = None, settings: Optional[AppSettings] = None, calibration: Optional[CalibrationConfig] = None) -> DocumentEvaluationReport`:
    - Coordinates complete 19-step workflow:
      1. Job UUID generation and document metadata initialization.
      2. Configuration and calibration resolution (`AppSettings()`, `CalibrationConfig.load_defaults()`).
      3. Security gate inspection (`inspect_and_validate_pdf`).
      4. UUID-isolated workspace creation (`create_job_workspace`).
      5. Safe PyMuPDF document opening and sequential page routing (`route_document_pages`).
      6. Table extraction across digital and hybrid pages via `pdfplumber` line-based ruling and coordinate fallback (`extract_tables_from_page`).
      7. Dynamic `table_presence` resolution: sets `CONFIRMED_PRESENT` when tables are found and `CONFIRMED_ABSENT` when pages are inspected with zero tables.
      8. Multipage table reconstruction with 7-factor evaluation and header stripping (`reconstruct_multipage_tables`).
      9. Structural integrity validation (`structural_checks_passed`).
      10. Table-level arithmetic consistency evaluation and Document Quality Gate evaluation (`evaluate_document_quality`).
      11. Peak Python heap measurement via `tracemalloc` when `enable_memory_measurement` is True.
      12. Strict `try ... finally` handle closure and workspace cleanup (`cleanup_job_workspace`), guaranteeing the original input file is never deleted.
  - `_build_controlled_failure`:
    - Catches operational exceptions (`SecurityGateError`, `FileNotFoundValidationError`, `FileSizeExceededError`, `InvalidPDFSignatureError`, `EncryptedPDFError`, `CorruptPDFError`, `PageCountExceededError`, `PathTraversalError`).
    - Returns structured `DocumentEvaluationReport` with `execution_state = JobExecutionState.FAILED` and `verification_status = VerificationStatus.FAILED` without leaking confidential document text.

## Verification Evidence
- `test_pipeline_digital_ruled_table`: Validates clean end-to-end table extraction and quality gate evaluation.
- `test_pipeline_corrupt_pdf_controlled_failure`: Validates corrupt PDF yields `FAILED` report without crashing.
- `test_pipeline_encrypted_pdf_controlled_failure`: Validates encrypted PDF yields controlled failure.
- `test_pipeline_nonexistent_file`: Validates nonexistent file returns controlled failure report.
