# SPEC.md — Project Specification

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: Specification finalized directly from `MASTER_DIRECTIVE.md`. Ready for phase planning and execution.

## Vision
DocuStruct AI is a deterministic-first, security-conscious document table extraction and verification system engineered for Windows 10/11 CPU environments. It converts digital PDF documents into auditable, structured tabular data while strictly preserving source evidence, maintaining exact arithmetic and geometry audit trails, and explicitly reporting uncertainty without hallucination or silent data mutation.

## Goals
1. **Deterministic Digital Table Extraction** — Extract structured tables from native digital PDFs using line-based geometry and coordinate interval strategies with PyMuPDF and pdfplumber without using OCR or LLMs.
2. **Immutable Source Evidence & Typed Contracts** — Maintain immutable `raw_value` across all cell records, type-safe Decimal normalization without binary float precision loss, and strict preservation of identifiers, leading zeros, and ragged rows.
3. **Conservative Multipage Reconstruction** — Stitch split tables across consecutive pages using seven deterministic decision factors (column overlap, header similarity, type compatibility, page geometry, row continuity, duplicate row preservation) without forcing ungrounded merges.
4. **Deterministic Arithmetic Consistency & Quality Gates** — Validate table totals and cross-foots using exact `Decimal` math, preserving source discrepancies (`SOURCE_ARITHMETIC_DISCREPANCY`), and assign document-level verification statuses (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`).
5. **Robust Security & Windows File-Handle Discipline** — Enforce a 25 MiB / 50-page security boundary, PDF structure validation, isolated UUID workspaces, path-traversal prevention, and guaranteed handle closure to prevent Windows file-locking failures during cleanup.
6. **Regression Evaluation Harness & Synthetic Fixtures** — Deliver a standalone evaluation harness for ground-truth benchmarking and reproducible PyMuPDF synthetic PDF fixtures covering all layout edge cases.

## Non-Goals (Out of Scope for Phase 1)
- **No OCR Engines** — No Tesseract, RapidOCR, OpenCV OCR, or raster table extraction in Phase 1 (scanned pages are classified and routed to `INCOMPLETE_DEFERRED_TO_OCR`).
- **No LLM / AI APIs** — No external cloud AI APIs, OpenAI, Anthropic, or hosted language models.
- **No Web / Presentation Frameworks** — No FastAPI, Flask, React, HTML UIs, or REST endpoints in Phase 1.
- **No Database / Cache / Workers** — No PostgreSQL, SQLite, Redis, Celery, or background task brokers.
- **No Spreadsheet Generation** — No `openpyxl`, `pandas`, or Excel workbook creation (formula risk is flagged in metadata only; serialization belongs to Phase 3).
- **No External Binary Toolchains** — No Java, Ghostscript, Poppler binaries, or `libmagic` native dependencies.
- **No Silent Deduplication / Padding** — Legitimate identical rows and ragged rows must never be pruned or artificially rectangularized.

## Constraints
- **Hardware Target**: Windows 10/11, CPU-only execution, 8–16 GB RAM ceiling, zero GPU requirement, zero paid cloud dependencies.
- **Concurrency & Memory**: Single document-processing worker (`max_workers = 1`), sequential page processing, bounded heap allocation, strict try/finally resource cleanup.
- **File Safety on Windows**: Mandatory closure of all `fitz.Document` and `pdfplumber.PDF` handles before workspace deletion or cleanup.
- **Permitted Dependencies**: Strictly limited to `pydantic>=2.7,<3.0`, `pydantic-settings>=2.2`, `PyYAML>=6.0`, `PyMuPDF>=1.24.0`, `pdfplumber>=0.11.0`, `rapidfuzz>=3.9.0`, and `pytest>=8.2.0`.
- **Measurement Integrity**: All extraction thresholds and accuracy metrics remain marked `UNMEASURED` until benchmarked against a verified ground-truth dataset.

## Success Criteria
- [ ] Complete Phase 1 modular codebase implemented in `backend/app/` according to Section 5 project structure.
- [ ] Strict Pydantic v2 domain models (`BoundingBox`, `CellRecord`, `StitchAuditEvent`, `ValidationIssue`, `CorrectionRecord`, `PageProfile`, `CanonicalTable`, `PageExtractionResult`, `DocumentEvaluationReport`) and state enums functional with full serialization.
- [ ] PDF Security Gate enforces 25 MiB limit, 50-page limit, %PDF signature validation, path-traversal protection, and UUID workspace isolation.
- [ ] Page Router accurately classifies pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE` without misclassifying pages containing images as scanned-only.
- [ ] Digital table extractor successfully extracts ruled and borderless tables from digital PDFs, retaining cell bounding boxes and extraction metadata.
- [ ] Multipage reconstructor reliably evaluates table pairs, logs `StitchAuditEvent` for every decision, and rejects merges when evidence contradicts continuity.
- [ ] Deterministic normalizer handles standard and Indian number groupings, accounting negatives, high-precision decimals, and identifier leading zeros without altering `raw_value`.
- [ ] Quality gate accurately assigns document status (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`) and detects arithmetic discrepancies without fabricating values.
- [ ] Complete pipeline coordinator (`run_phase1_pipeline`) executes end-to-end and returns a validated `DocumentEvaluationReport`.
- [ ] 100% passing unit tests executed via `pytest -v` across all required test suites, with no mock bypasses, no hardcoded fixture filenames, and zero unclosed file handles on Windows.
- [ ] Standalone regression evaluation harness executed and documented with real test case counts.

---

*Last updated: 2026-10-15 (Derived from MASTER_DIRECTIVE.md)*
