---
milestone: v1.0
updated: 2026-10-15T13:20:00+05:30
---

# REQUIREMENTS.md — Formal Requirements Tracking

## Overview
Requirements derived directly from `MASTER_DIRECTIVE.md` and `.gsd/SPEC.md` for full traceability, test verification, and implementation coverage.

---

## Functional Requirements

| ID | Requirement | Source | Phase | Status |
|----|-------------|--------|-------|--------|
| REQ-01 | Config & calibration loader with typed Pydantic settings, `thresholds.yaml` parser, explicit units, and path independence | SPEC Goal 5 | Phase 1 | Complete |
| REQ-02 | Typed state enumerations (`JobExecutionState`, `VerificationStatus`, `PageType`, `PageProcessingStatus`, `TablePresenceStatus`, `ValidationOutcome`, `StitchDecision`, `CellQualityStatus`, `DataType`) | SPEC Goal 2 | Phase 1 | Complete |
| REQ-03 | Pydantic v2 domain models (`BoundingBox`, `CellRecord`, `StitchAuditEvent`, `ValidationIssue`, `CorrectionRecord`, `PageProfile`, `CanonicalTable`, `PageExtractionResult`, `DocumentEvaluationReport`) with immutable `raw_value` | SPEC Goal 2 | Phase 1 | Complete |
| REQ-04 | PDF security gate enforcing 25 MiB file size limit, 50 page limit, `%PDF-` signature check, explicit rejection of encrypted/password-protected PDFs, rejection of zero-page PDFs, UUID workspace isolation, path-traversal prevention, and strict preservation ensuring the user's original input file is never deleted | SPEC Goal 5 | Phase 1 | Complete |
| REQ-05 | Page classifier routing pages into `DIGITAL`, `SCANNED`, `HYBRID`, and `EMPTY_OR_UNREADABLE` via character count, garbled ratio, image coverage, and vector lines | SPEC Goal 1 | Phase 2 | Complete |
| REQ-06 | Deterministic normalizer preserving `raw_value`, parsing standard & Indian number groupings, accounting negatives, high-precision decimals, identifier leading zeros, and formula-risk detection for nonnumeric STRING/IDENTIFIER cells starting with `=`, `+`, `-`, `@`, tab (`\t`), or carriage return (`\r`) without prepending apostrophes or mutating cell values (valid numeric negatives like `-450.50` must not trigger formula-risk) | SPEC Goal 2 | Phase 2 | Complete |
| REQ-07 | Digital table extractor utilizing line-based (pdfplumber) and coordinate-interval fallback strategies for ruled and borderless tables | SPEC Goal 1 | Phase 2 | Complete |
| REQ-08 | Conservative multipage table reconstructor assessing 7 decision factors with configurable defaults (`stitch_min_relative_col_overlap = 0.75`, `header_similarity_confirm = 0.85`, `stitch_min_type_compatibility = 0.85`), table-relative column overlap, multiline header stripping using a 1–3 row sliding window, and generating structured `StitchAuditEvent` records | SPEC Goal 3 | Phase 3 | Complete |
| REQ-09 | Evidence-gated cell correction contract requiring independent deterministic evidence strictly from permitted sources (`NATIVE_PDF_CHAR_STREAM`, `INDEPENDENT_WORD_COORDINATES`, `VECTOR_GRID_GEOMETRY`), preserving `raw_value`, recording `CorrectionRecord`, never auto-balancing totals, and storing algebraic candidates only in `inferred_candidate_value` with `ILLEGIBLE_OR_MISSING` status | SPEC Goal 2 | Phase 3 | Complete |
| REQ-10 | Deterministic arithmetic consistency evaluator via `evaluate_table_arithmetic_consistency(table: CanonicalTable) -> tuple[ValidationOutcome, list[ValidationIssue]]` using exact `Decimal` math for total rows/columns, reporting `SOURCE_ARITHMETIC_DISCREPANCY` or `ARITHMETIC_SCOPE_AMBIGUOUS` without auto-correcting values or falsely corroborating cells | SPEC Goal 4 | Phase 4 | Complete |
| REQ-11 | Document quality gate evaluating full-document verification status (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`) following conservative decision precedence (Execution failure → Completeness → Table presence → Anomalies/Stitches → Math → Verification status), emitting reason codes (`NO_TABLES_FOUND`, `OCR_REQUIRED_FOR_SCANNED_CONTENT`), and attaching the mandatory verbatim disclaimer: "Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text." | SPEC Goal 4 | Phase 4 | Complete |
| REQ-12 | End-to-end pipeline coordinator via `run_phase1_pipeline(file_path: Path, original_filename: Optional[str] = None, settings: Optional[AppSettings] = None, calibration: Optional[CalibrationConfig] = None) -> DocumentEvaluationReport` executing ingestion, routing, extraction, normalization, stitching, verification, safe error reporting, and guaranteed resource cleanup | SPEC Goal 1-5 | Phase 5 | Complete |
| REQ-13 | Windows file-handle safety ensuring guaranteed closure of PyMuPDF and pdfplumber resources before temporary workspace cleanup | SPEC Goal 5 | Phase 1-5 | Complete |
| REQ-14 | Synthetic PDF test fixtures created via PyMuPDF drawing primitives covering ruled, borderless, multipage, duplicate rows, scanned-like, and arithmetic discrepancy layouts | SPEC Goal 6 | Phase 5 | Complete |
| REQ-15 | Regression evaluation harness (`regression_harness.py`) providing verifiable metrics reporting for ground-truth benchmarking | SPEC Goal 6 | Phase 5 | Complete |

---

## Non-Functional Requirements

| ID | Requirement | Category | Phase | Status |
|----|-------------|----------|-------|--------|
| NFR-01 | Memory discipline: Sequential page processing (`max_workers = 1`), bounded heap allocation for 8–16 GB RAM systems, optional `tracemalloc` measurement recording `peak_python_heap_bytes` (clarifying that Python heap usage is not total operating-system process RAM) | Performance | All | Complete |
| NFR-02 | Resource safety: Guaranteed handle closure on Windows 10/11, preventing `PermissionError` during workspace cleanup | Reliability | All | Complete |
| NFR-03 | Dependency hygiene: Zero external unapproved dependencies; strictly restricted to the 7 approved packages | Security | Phase 1 | Complete |
| NFR-04 | Audit integrity: No synthetic or hardcoded ground truth reported as measured real-world accuracy; uncalibrated metrics remain `UNMEASURED` | Integrity | Phase 5 | Complete |

---

## Constraints

| ID | Constraint | Source | Impact |
|----|------------|--------|--------|
| CON-01 | CPU-only Windows 10/11 environment, 8–16 GB RAM, no GPU requirement; Python 3.11 target with compatibility for Python >=3.10 and <3.13 | MASTER_DIRECTIVE Sec 3 | Sequential processing, no heavy deep learning, strict environment targeting |
| CON-02 | No OCR, LLMs, FastAPI, React, openpyxl, pandas, or external binaries (Ghostscript/Poppler/libmagic) | MASTER_DIRECTIVE Sec 2 | Phase 1 scope boundary strictly enforced |
| CON-03 | Exact Decimal arithmetic — binary `float` strictly forbidden for cell values and sum calculations | MASTER_DIRECTIVE Sec 12, 16 | Avoid precision artifacts in currency and totals |
| CON-04 | Immutability of `raw_value` across all stages of extraction and normalization | MASTER_DIRECTIVE Sec 9, 12, 24 | Complete auditability and provenance |

---

## Traceability Matrix

| Requirement | Plans | Target Module | Tests |
|-------------|-------|---------------|-------|
| REQ-01 | 1.1 | `backend/app/config/` | `tests/unit/test_step_1_1_config.py` |
| REQ-02 | 1.2 | `backend/app/models/state.py` | `tests/unit/test_step_1_2_status_and_gates.py` |
| REQ-03 | 1.2 | `backend/app/models/domain.py` | `tests/unit/test_step_1_2_status_and_gates.py` |
| REQ-04 | 1.3 | `backend/app/ingestion/security_gate.py` | `tests/unit/test_step_1_3_security_gate.py` |
| REQ-05 | 2.1 | `backend/app/ingestion/page_router.py` | `tests/unit/test_step_1_4_page_router.py` |
| REQ-06 | 2.2 | `backend/app/extraction/normalizer.py` | `tests/unit/test_normalizer_integrity.py` |
| REQ-07 | 2.3 | `backend/app/extraction/digital_extractor.py` | `tests/unit/test_step_1_5_digital_extractor.py` |
| REQ-08 | 3.1 | `backend/app/extraction/table_reconstructor.py` | `tests/unit/test_step_1_6_table_reconstructor.py` |
| REQ-09 | 3.2 | `backend/app/extraction/table_reconstructor.py` | `tests/unit/test_step_1_6_table_reconstructor.py` |
| REQ-10 | 4.1 | `backend/app/verification/quality_gate.py` | `tests/unit/test_quality_gate.py` |
| REQ-11 | 4.2 | `backend/app/verification/quality_gate.py` | `tests/unit/test_quality_gate.py` |
| REQ-12 | 5.1 | `backend/app/pipeline.py` | `tests/unit/test_phase1_pipeline.py` |
| REQ-13 | 1-5 | All modules (`fitz` / `pdfplumber` managers) | All test suites |
| REQ-14 | 5.2 | `backend/tests/conftest.py` | All test suites |
| REQ-15 | 5.3 | `backend/tests/evaluation/regression_harness.py` | Evaluation harness execution |
