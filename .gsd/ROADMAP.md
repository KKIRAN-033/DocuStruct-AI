---
milestone: v1.0
version: 1.0.0
updated: 2026-10-15T13:21:00+05:30
---

# ROADMAP.md — DocuStruct AI Phase 1 Implementation

> **Current Phase:** 1 - Foundation, Domain Models & Ingestion Security
> **Status:** ⬜ Ready for Planning

## Must-Haves (from SPEC)
- [ ] Strict Pydantic v2 domain models and typed state enumerations with immutable `raw_value`
- [ ] PDF security gate enforcing 25 MiB / 50-page limits and path-traversal protection
- [ ] Page router classifying pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE`
- [ ] Native digital table extraction using ruling lines and coordinate intervals without OCR/LLMs
- [ ] Deterministic normalizer supporting Indian/standard grouping, negatives, and identifier zero preservation
- [ ] Conservative multipage table reconstructor implementing 7 decision factors and audit trail
- [ ] Exact Decimal arithmetic validator detecting `SOURCE_ARITHMETIC_DISCREPANCY`
- [ ] Document quality gate assigning comprehensive document verification status
- [ ] End-to-end pipeline coordinator (`run_phase1_pipeline`) with guaranteed Windows file-handle cleanup
- [ ] Reproducible synthetic PDF fixtures and standalone regression evaluation harness

---

## Phases

### Phase 1: Foundation, Domain Models & Ingestion Security
**Status:** ⬜ Not Started
**Objective:** Establish backend package structure, typed configuration loading (`settings.py`, `calibration.py`, `thresholds.yaml`), state enums (`state.py`), domain model contracts (`domain.py`), PDF security gate (`security_gate.py`), and corresponding unit tests.
**Requirements:** REQ-01, REQ-02, REQ-03, REQ-04, REQ-13, NFR-01, NFR-02, NFR-03

**Plans:**
- [ ] Plan 1.1: Project scaffolding, packaging configuration (`pyproject.toml`, `requirements.txt`), and configuration/calibration system (`settings.py`, `calibration.py`, `thresholds.yaml`)
- [ ] Plan 1.2: State enumerations (`state.py`) and typed Pydantic v2 domain models (`domain.py`) with validation and serialization
- [ ] Plan 1.3: PDF security gate (`security_gate.py`) with file inspection, UUID workspace isolation, and path-traversal checks
- [ ] Plan 1.4: Unit test suite for Phase 1 foundations (`test_step_1_1_config.py`, `test_step_1_2_status_and_gates.py`, `test_step_1_3_security_gate.py`)

---

### Phase 2: Page Routing, Normalization & Digital Extraction
**Status:** ⬜ Not Started
**Objective:** Implement deterministic page classification (`page_router.py`), cell normalization and formula-risk detection (`normalizer.py`), and native digital table extraction (`digital_extractor.py`) using ruling-line and coordinate interval strategies.
**Depends on:** Phase 1
**Requirements:** REQ-05, REQ-06, REQ-07, REQ-13, NFR-01

**Plans:**
- [ ] Plan 2.1: Page router (`page_router.py`) with explainable signal detection and sequential resource discipline
- [ ] Plan 2.2: Deterministic normalizer (`normalizer.py`) for whitespace, standard/Indian grouping, accounting negatives, high-precision decimals, and formula-risk boundary
- [ ] Plan 2.3: Native digital table extractor (`digital_extractor.py`) using line-based geometry and coordinate fallback
- [ ] Plan 2.4: Unit test suite for Phase 2 (`test_step_1_4_page_router.py`, `test_normalizer_integrity.py`, `test_step_1_5_digital_extractor.py`)

---

### Phase 3: Multipage Reconstruction & Evidence-Gated Corrections
**Status:** ⬜ Not Started
**Objective:** Implement conservative cross-page table stitcher (`table_reconstructor.py`) evaluating the 7 decision factors, multiline header stripping, and evidence-gated correction contracts.
**Depends on:** Phase 2
**Requirements:** REQ-08, REQ-09, REQ-13

**Plans:**
- [ ] Plan 3.1: Multipage table reconstructor (`table_reconstructor.py`) with 7-factor evaluation and `StitchAuditEvent` logging
- [ ] Plan 3.2: Evidence-gated cell correction contracts (`CorrectionRecord`) and candidate preservation
- [ ] Plan 3.3: Unit test suite for Phase 3 (`test_step_1_6_table_reconstructor.py`) covering continuation, rejection, serial indices, and duplicate preservation

---

### Phase 4: Deterministic Arithmetic Consistency & Document Quality Gate
**Status:** ⬜ Not Started
**Objective:** Implement table arithmetic evaluator (`quality_gate.py`) using exact Decimal calculations, source discrepancy reporting, and document-level quality gate evaluation.
**Depends on:** Phase 3
**Requirements:** REQ-10, REQ-11, REQ-13

**Plans:**
- [ ] Plan 4.1: Deterministic arithmetic evaluator (`evaluate_table_arithmetic_consistency`) with total row/column detection and discrepancy flagging
- [ ] Plan 4.2: Document quality gate evaluating execution state, page completeness, anomalies, and assigning `VerificationStatus` with mandatory disclaimers
- [ ] Plan 4.3: Unit test suite for Phase 4 arithmetic and quality gate logic

---

### Phase 5: Pipeline Integration, Evaluation Harness & Developer Experience
**Status:** ⬜ Not Started
**Objective:** Assemble the end-to-end pipeline coordinator (`pipeline.py: run_phase1_pipeline`), synthetic PDF fixtures generator (`conftest.py`), standalone regression evaluation harness (`regression_harness.py`), developer documentation, and execute full verification.
**Depends on:** Phase 4
**Requirements:** REQ-12, REQ-13, REQ-14, REQ-15, NFR-01, NFR-02, NFR-04

**Plans:**
- [ ] Plan 5.1: End-to-end pipeline coordinator (`pipeline.py`) with guaranteed Windows file-handle cleanup and safe error reporting
- [ ] Plan 5.2: Synthetic PDF test fixtures (`conftest.py`) covering ruled, borderless, multipage, and anomaly layouts
- [ ] Plan 5.3: Ground-truth regression evaluation harness (`regression_harness.py`) and evaluation cases format
- [ ] Plan 5.4: Developer documentation (`README.md`, `.gitignore`) and comprehensive test execution report
