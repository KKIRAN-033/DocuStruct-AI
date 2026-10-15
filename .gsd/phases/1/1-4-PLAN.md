---
phase: 1
plan: 4
wave: 3
depends_on: [1.1, 1.2, 1.3]
---

# Plan 1.4: Phase 1 Foundations Unit Test Suite

## Objective
Implement synthetic PDF test fixtures (`conftest.py`) and author comprehensive unit tests covering configuration (`test_step_1_1_config.py`), state models and domain contracts (`test_step_1_2_status_and_gates.py`), and the PDF security gate (`test_step_1_3_security_gate.py`).

## Context
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md` (REQ-01, REQ-02, REQ-03, REQ-04, REQ-13, REQ-14)
- `MASTER_DIRECTIVE.md` (Sections 5, 7, 8, 9, 10, 19, 20)
- `.gsd/phases/1/RESEARCH.md`

## Tasks

<task type="auto">
  <name>Create test fixtures and configuration unit tests</name>
  <files>
    backend/tests/conftest.py
    backend/tests/unit/test_step_1_1_config.py
  </files>
  <action>
    1. Create backend/tests/conftest.py:
       Define pytest fixtures generating synthetic PDFs using PyMuPDF:
       - valid_digital_pdf: minimal 1-page valid PDF with text.
       - zero_page_pdf: empty/zero-page PDF constructed via fitz.open().
       - multipage_51_pdf: PDF with 51 blank pages.
       - encrypted_pdf: PDF created and saved with encryption / user_pw.
       - corrupt_pdf_file: file with valid %PDF- header but truncated corrupt stream.
       - non_pdf_file: plain text or binary file without %PDF- header.
       - isolated_test_dir: temporary directory fixture.

    2. Create backend/tests/unit/test_step_1_1_config.py:
       Implement tests for Section 7 requirements:
       - test_default_settings_loading: verify all defaults (25 MiB, 50 pages, 1 worker).
       - test_settings_environment_override: verify DOCUSTRUCT_* env var overrides.
       - test_missing_thresholds_yaml: verify ConfigurationError raised on missing file.
       - test_malformed_thresholds_yaml: verify ConfigurationError on corrupt syntax.
       - test_invalid_threshold_ranges: verify validation error on out-of-range thresholds.
       - test_path_independent_config_loading: execute loading from arbitrary working directories.
  </action>
  <verify>
    powershell -Command "cd backend; pytest -v tests/unit/test_step_1_1_config.py"
  </verify>
  <done>
    Synthetic PDF fixtures functional in conftest.py; 100% passing tests in test_step_1_1_config.py proving path-independent config and typed validation.
  </done>
</task>

<task type="auto">
  <name>Create unit tests for state enums, domain models, and security gate</name>
  <files>
    backend/tests/unit/test_step_1_2_status_and_gates.py
    backend/tests/unit/test_step_1_3_security_gate.py
  </files>
  <action>
    1. Create backend/tests/unit/test_step_1_2_status_and_gates.py:
       Implement tests for Section 8 & 9 requirements:
       - test_all_state_enums_values: verify 9 enums match MASTER_DIRECTIVE string values.
       - test_bounding_box_normalized_coordinates: verify norm_x0, norm_y0 and geometry bounds.
       - test_cell_record_immutability: verify raw_value cannot be overwritten; Decimal precision preserved without float conversion.
       - test_domain_model_serialization: verify full JSON serialization/deserialization of DocumentEvaluationReport.

    2. Create backend/tests/unit/test_step_1_3_security_gate.py:
       Implement tests for Section 10 & 19 requirements:
       - test_security_gate_missing_file: FileNotFoundError.
       - test_security_gate_directory_input: InvalidFileTypeError.
       - test_security_gate_empty_file: SecurityGateError.
       - test_security_gate_invalid_signature: InvalidPDFSignatureError.
       - test_security_gate_corrupt_pdf: CorruptPDFError.
       - test_security_gate_encrypted_pdf: EncryptedPDFError.
       - test_security_gate_zero_page_pdf: PageCountExceededError.
       - test_security_gate_page_count_over_50: PageCountExceededError.
       - test_security_gate_oversized_file: FileSizeExceededError.
       - test_security_gate_path_traversal: PathTraversalError.
       - test_security_gate_valid_pdf_metadata: returns valid page_count, file_size.
       - test_workspace_isolation_and_containment: UUID directory created safely.
       - test_workspace_cleanup_preserves_original_file: verify original input file is never deleted.
       - test_file_handle_closure_on_exception: verify fitz.Document handles closed before cleanup.
  </action>
  <verify>
    powershell -Command "cd backend; pytest -v tests/unit/test_step_1_2_status_and_gates.py tests/unit/test_step_1_3_security_gate.py"
  </verify>
  <done>
    100% passing tests across test_step_1_2_status_and_gates.py and test_step_1_3_security_gate.py with meaningful assertions, no mocked bypasses, and zero unclosed file handles.
  </done>
</task>

## Success Criteria
- [ ] PyMuPDF drawing fixtures in `conftest.py` generate synthetic PDFs reproducibly.
- [ ] `test_step_1_1_config.py` passes all configuration and calibration test cases.
- [ ] `test_step_1_2_status_and_gates.py` verifies all 9 enums, BoundingBox geometry, CellRecord immutability, and Decimal precision.
- [ ] `test_step_1_3_security_gate.py` verifies all 13 security and Windows handle safety rules.
- [ ] Zero unclosed file handles on Windows during test execution.
