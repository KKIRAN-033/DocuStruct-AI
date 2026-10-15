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
- **Python Environment**: Target Python 3.11 with compatibility for Python >=3.10 and <3.13.
- **Concurrency & Memory**: Single document-processing worker (`max_workers = 1`), sequential page processing, bounded heap allocation, strict try/finally resource cleanup. Optional `tracemalloc` heap measurement recording `peak_python_heap_bytes` (clarifying that Python heap usage is not total operating-system process RAM).
- **File Safety on Windows**: Mandatory closure of all `fitz.Document` and `pdfplumber.PDF` handles before workspace deletion or cleanup. The user's original input file must never be deleted.
- **Permitted Dependencies**: Strictly limited to `pydantic>=2.7,<3.0`, `pydantic-settings>=2.2`, `PyYAML>=6.0`, `PyMuPDF>=1.24.0`, `pdfplumber>=0.11.0`, `rapidfuzz>=3.9.0`, and `pytest>=8.2.0`.
- **Measurement Integrity**: All extraction thresholds and accuracy metrics remain marked `UNMEASURED` until benchmarked against a verified ground-truth dataset.

## Success Criteria
- [ ] Complete Phase 1 modular codebase implemented in `backend/app/` according to Section 5 project structure.
- [ ] Strict Pydantic v2 domain models (`BoundingBox`, `CellRecord`, `StitchAuditEvent`, `ValidationIssue`, `CorrectionRecord`, `PageProfile`, `CanonicalTable`, `PageExtractionResult`, `DocumentEvaluationReport`) and state enums functional with full serialization.
- [ ] PDF Security Gate enforces 25 MiB limit, 50-page limit, %PDF signature validation, path-traversal protection, UUID workspace isolation, explicit rejection of encrypted/password-protected and zero-page PDFs, and never deletes the user's original input file.
- [ ] Page Router accurately classifies pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE` without misclassifying pages containing images as scanned-only.
- [ ] Digital table extractor successfully extracts ruled and borderless tables from digital PDFs, retaining cell bounding boxes and extraction metadata.
- [ ] Multipage reconstructor reliably evaluates table pairs using configurable defaults (`stitch_min_relative_col_overlap = 0.75`, `header_similarity_confirm = 0.85`, `stitch_min_type_compatibility = 0.85`), sliding window of 1–3 leading rows for repeated-header evaluation, logs `StitchAuditEvent` for every decision, and rejects merges when evidence contradicts continuity.
- [ ] Deterministic normalizer handles standard and Indian number groupings, accounting negatives, high-precision decimals, identifier leading zeros without altering `raw_value`, and detects formula-risk prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`) for nonnumeric cells without modifying source values or prepending apostrophes (valid negative numeric values like `-450.50` must not trigger formula-risk).
- [ ] Evidence-gated cell corrections strictly require independent deterministic evidence from permitted sources (`NATIVE_PDF_CHAR_STREAM`, `INDEPENDENT_WORD_COORDINATES`, `VECTOR_GRID_GEOMETRY`) without fabricating values or auto-balancing totals.
- [ ] Quality gate accurately evaluates arithmetic consistency via `evaluate_table_arithmetic_consistency(table: CanonicalTable) -> tuple[ValidationOutcome, list[ValidationIssue]]` with `SOURCE_ARITHMETIC_DISCREPANCY` and `ARITHMETIC_SCOPE_AMBIGUOUS`, applies conservative decision precedence, assigns document status (`VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`), attaches reason codes (`NO_TABLES_FOUND`, `OCR_REQUIRED_FOR_SCANNED_CONTENT`), and includes the mandatory verbatim disclaimer: "Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."
- [ ] Complete pipeline coordinator (`run_phase1_pipeline(file_path: Path, original_filename: Optional[str] = None, settings: Optional[AppSettings] = None, calibration: Optional[CalibrationConfig] = None) -> DocumentEvaluationReport`) executes end-to-end and returns a validated `DocumentEvaluationReport`.
- [ ] 100% passing unit tests executed via `pytest -v` across all required test suites, with no mock bypasses, no hardcoded fixture filenames, and zero unclosed file handles on Windows.
- [ ] Standalone regression evaluation harness executed and documented with real test case counts.

---

*Last updated: 2026-10-15 (Derived from MASTER_DIRECTIVE.md)*
