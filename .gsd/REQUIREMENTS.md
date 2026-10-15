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
| REQ-01 | Config & calibration loader with typed Pydantic settings, `thresholds.yaml` parser, explicit units, and path independence | SPEC Goal 5 | Phase 1 | Pending |
| REQ-02 | Typed state enumerations (`JobExecutionState`, `VerificationStatus`, `PageType`, `PageProcessingStatus`, `TablePresenceStatus`, `ValidationOutcome`, `StitchDecision`, `CellQualityStatus`, `DataType`) | SPEC Goal 2 | Phase 1 | Pending |
| REQ-03 | Pydantic v2 domain models (`BoundingBox`, `CellRecord`, `StitchAuditEvent`, `ValidationIssue`, `CorrectionRecord`, `PageProfile`, `CanonicalTable`, `PageExtractionResult`, `DocumentEvaluationReport`) with immutable `raw_value` | SPEC Goal 2 | Phase 1 | Pending |
| REQ-04 | PDF security gate enforcing 25 MiB file size limit, 50 page limit, `%PDF-` signature check, UUID workspace isolation, and path-traversal prevention | SPEC Goal 5 | Phase 1 | Pending |
| REQ-05 | Page classifier routing pages into `DIGITAL`, `SCANNED`, `HYBRID`, and `EMPTY_OR_UNREADABLE` via character count, garbled ratio, image coverage, and vector lines | SPEC Goal 1 | Phase 2 | Pending |
| REQ-06 | Deterministic normalizer preserving `raw_value`, parsing standard & Indian number groupings, accounting negatives, high-precision decimals, identifier leading zeros, and formula-risk detection | SPEC Goal 2 | Phase 2 | Pending |
| REQ-07 | Digital table extractor utilizing line-based (pdfplumber) and coordinate-interval fallback strategies for ruled and borderless tables | SPEC Goal 1 | Phase 2 | Pending |
| REQ-08 | Conservative multipage table reconstructor assessing 7 decision factors, multiline header stripping, and generating structured `StitchAuditEvent` records | SPEC Goal 3 | Phase 3 | Pending |
| REQ-09 | Evidence-gated cell correction contract requiring independent deterministic evidence, preserving `raw_value`, and recording `CorrectionRecord` | SPEC Goal 2 | Phase 3 | Pending |
| REQ-10 | Deterministic arithmetic consistency evaluator using exact `Decimal` math for total rows/columns, reporting `SOURCE_ARITHMETIC_DISCREPANCY` without auto-correcting | SPEC Goal 4 | Phase 4 | Pending |
| REQ-11 | Document quality gate evaluating full-document verification status (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`) with mandatory disclaimers | SPEC Goal 4 | Phase 4 | Pending |
| REQ-12 | End-to-end pipeline coordinator (`run_phase1_pipeline`) executing ingestion, routing, extraction, normalization, stitching, verification, and returning `DocumentEvaluationReport` | SPEC Goal 1-5 | Phase 5 | Pending |
| REQ-13 | Windows file-handle safety ensuring guaranteed closure of PyMuPDF and pdfplumber resources before temporary workspace cleanup | SPEC Goal 5 | Phase 1-5 | Pending |
| REQ-14 | Synthetic PDF test fixtures created via PyMuPDF drawing primitives covering ruled, borderless, multipage, duplicate rows, scanned-like, and arithmetic discrepancy layouts | SPEC Goal 6 | Phase 5 | Pending |
| REQ-15 | Regression evaluation harness (`regression_harness.py`) providing verifiable metrics reporting for ground-truth benchmarking | SPEC Goal 6 | Phase 5 | Pending |

---

## Non-Functional Requirements

| ID | Requirement | Category | Phase | Status |
|----|-------------|----------|-------|--------|
| NFR-01 | Memory discipline: Sequential page processing (`max_workers = 1`), bounded heap allocation for 8–16 GB RAM systems | Performance | All | Pending |
| NFR-02 | Resource safety: Guaranteed handle closure on Windows 10/11, preventing `PermissionError` during workspace cleanup | Reliability | All | Pending |
| NFR-03 | Dependency hygiene: Zero external unapproved dependencies; strictly restricted to the 7 approved packages | Security | Phase 1 | Pending |
| NFR-04 | Audit integrity: No synthetic or hardcoded ground truth reported as measured real-world accuracy; uncalibrated metrics remain `UNMEASURED` | Integrity | Phase 5 | Pending |

---

## Constraints

| ID | Constraint | Source | Impact |
|----|------------|--------|--------|
| CON-01 | CPU-only Windows 10/11 environment, 8–16 GB RAM, no GPU requirement | MASTER_DIRECTIVE Sec 3 | Sequential processing, no heavy deep learning |
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
| REQ-10 | 4.1 | `backend/app/verification/quality_gate.py` | `tests/unit/test_phase1_pipeline.py` |
| REQ-11 | 4.2 | `backend/app/verification/quality_gate.py` | `tests/unit/test_step_1_2_status_and_gates.py` |
| REQ-12 | 5.1 | `backend/app/pipeline.py` | `tests/unit/test_phase1_pipeline.py` |
| REQ-13 | 1-5 | All modules (`fitz` / `pdfplumber` managers) | All test suites |
| REQ-14 | 5.2 | `backend/tests/conftest.py` | All test suites |
| REQ-15 | 5.3 | `backend/tests/evaluation/regression_harness.py` | Evaluation harness execution |
