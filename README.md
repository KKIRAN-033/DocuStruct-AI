# DocuStruct AI

> **Extract. Verify. Correct. Deliver.**  
> *Deterministic-first document table extraction, auditable verification, and evidence-gated reconstruction.*

---

## 1. Product Overview

DocuStruct AI is a deterministic-first document intelligence framework designed to extract, reconstruct, verify, and deliver structured tabular data from PDF documents with rigorous mathematical consistency and full auditability.

### The Problem
Traditional document extraction tools frequently treat document tables as opaque text blocks or rely exclusively on probabilistic Large Language Models (LLMs) or unverified OCR heuristics. This leads to silent hallucinations, dropped decimal precision, altered identifiers, corrupted accounting negatives, and unprovable totals.

### The DocuStruct AI Philosophy
1. **Deterministic-First**: Native vector and character geometry extraction takes precedence over probabilistic models.
2. **Immutability of Source Evidence**: The original extracted text (`raw_value`) is preserved immutably throughout all processing stages.
3. **Exact Decimal Arithmetic**: All numbers, sums, and currency calculations use Python's exact `Decimal` representation—binary floating-point arithmetic is strictly prohibited.
4. **Evidence-Gated Corrections**: OCR-error corrections are accepted only when corroborated by independent deterministic signals from approved sources; totals are never auto-balanced or fabricated.
5. **Separation of Execution and Verification**: A document that successfully processes without software crashes can still fail verification due to source arithmetic discrepancies or uninspected scanned pages.

---

## 2. Phase 1 Implementation Scope

Phase 1 establishes the deterministic extraction and verification core:
- **PDF Security Ingestion Gate**: File size limit (25 MiB), page count limit (50 pages), `%PDF-` header validation, password/encryption rejection, zero-page rejection, path-traversal prevention, UUID-isolated workspaces, and guaranteed input file preservation.
- **Explainable Page Router**: Signals analysis (printable character counts, garbled-character ratios, raster image coverage, vector lines) classifying pages into `DIGITAL`, `SCANNED`, `HYBRID`, or `EMPTY_OR_UNREADABLE` without heavy pixmap rendering.
- **Deterministic Normalizer**: Normalizes whitespace, standard and Indian numbering systems (`1,23,456.78`), accounting negatives (`(100.00)` $\to$ `-100.00`, `100.00-` $\to$ `-100.00`), preserves identifier leading zeros (`"00123"` $\to$ `IDENTIFIER`), and detects formula-risk prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`) without mutating cell values or prepending apostrophes.
- **Native Digital Table Extractor**: Dual-strategy line-based ruling extraction (via `pdfplumber`) with coordinate-interval fallback clustering for borderless tables. Preserves ragged rows and legitimate duplicate transactions.
- **Conservative Multipage Table Reconstructor**: Evaluates 7 deterministic factors across page boundaries (column counts, table-relative column overlap, header similarity via RapidFuzz, cell data-type compatibility, page transition sequence, reading-flow continuity, and serial numbering continuity) with sliding-window header stripping (1–3 rows).
- **Deterministic Table Arithmetic Consistency Evaluator**: Detects summary rows (`TOTAL`, `SUBTOTAL`, `GRAND_TOTAL`), verifies sums with exact `Decimal` calculations (0.001 tolerance), flags mismatches as `SOURCE_ARITHMETIC_DISCREPANCY`, detects `ARITHMETIC_SCOPE_AMBIGUOUS`, and never falsely corroborates contributing cells.
- **Conservative Document Quality Gate**: Assigns document-level `VerificationStatus` using strict 9-level conservative decision precedence and attaches the mandatory verbatim disclaimer.
- **End-to-End Pipeline Coordinator**: `run_phase1_pipeline` coordinating all 19 steps with guaranteed Windows file-handle safety, try/finally resource cleanup, and optional `tracemalloc` peak Python heap measurement.

### Explicitly Unbuilt Features (Future Phases)
The following features are **NOT implemented in Phase 1** and are reserved for future roadmap milestones:
- ❌ **OCR Engines** (Tesseract, EasyOCR, PaddleOCR, cloud vision APIs) — Scanned pages are safely deferred with `OCR_REQUIRED_FOR_SCANNED_CONTENT`.
- ❌ **Large Language Models (LLMs)** — No OpenAI, Anthropic, Gemini, or local Ollama dependencies.
- ❌ **Web UI & REST APIs** — No FastAPI, Flask, Django, React, or frontend frameworks.
- ❌ **Heavy Binaries** — No Ghostscript, Poppler, or system-level binary dependencies.
- ❌ **Dataframe Libraries** — No pandas, polars, or openpyxl.

---

## 3. System Requirements & Prerequisites

- **Operating System**: Windows 10 or Windows 11 (64-bit).
- **Hardware**: CPU-only, 8–16 GB system RAM (no GPU required).
- **Python Version**: Python 3.11 (tested on 3.11.9, compatible with Python $\ge$ 3.10 and < 3.13).
- **Shell**: Microsoft PowerShell 5.1 or PowerShell 7+.

---

## 4. Installation & Environment Setup

Run the following commands in PowerShell from the repository root:

```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Upgrade pip and install approved dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Approved Dependencies (Strict 7-Package List)
DocuStruct AI Phase 1 operates under a strict dependency hygiene contract:
1. `pydantic` ($\ge$ 2.0) — Strict schema validation and typed domain models.
2. `pydantic-settings` — Typed environment and configuration loading.
3. `PyYAML` — Calibration threshold loading (`thresholds.yaml`).
4. `PyMuPDF` (v1.28+) — PDF geometry, text, vector drawing analysis, and synthetic test fixtures.
5. `pdfplumber` — Line-based ruling extraction and coordinate word positions.
6. `rapidfuzz` — Normalized Levenshtein ratio for fuzzy header matching.
7. `pytest` — Comprehensive test execution framework.

---

## 5. Running the Pipeline

You can invoke the pipeline programmatically via Python:

```python
from pathlib import Path
from app.pipeline import run_phase1_pipeline
from app.config.settings import AppSettings

# Run pipeline on a document
pdf_path = Path("sample_document.pdf")
report = run_phase1_pipeline(pdf_path)

print(f"Job ID: {report.job_id}")
print(f"Execution State: {report.execution_state.value}")
print(f"Verification Status: {report.verification_status.value}")
print(f"Tables Extracted: {len(report.canonical_tables)}")
print(f"Status Reasons: {report.status_reason_codes}")
print(f"Disclaimer: {report.limitation_disclaimers[0]}")
```

---

## 6. Execution States vs. Verification Status

DocuStruct AI strictly separates pipeline execution progress from verification outcomes:

### Execution State (`JobExecutionState`)
Tracks pipeline lifecycle execution:
- `COMPLETED`: The pipeline executed all applicable processing steps without crashing.
- `FAILED`: An unrecoverable operational failure occurred (e.g. invalid signature, corrupted file, password-protected PDF, file size limit exceeded).

### Verification Status (`VerificationStatus`)
Assigned by the Document Quality Gate following conservative decision precedence:
1. **`FAILED`**: 
   - Execution failure (`JobExecutionState.FAILED`); or
   - Fully inspected digital document with 0 extractable tables and all pages `CONFIRMED_ABSENT` (Reason: `NO_TABLES_FOUND`).
2. **`REVIEW_REQUIRED`**:
   - Scanned pages present (Reason: `OCR_REQUIRED_FOR_SCANNED_CONTENT`).
   - Unextracted raster regions on hybrid pages (Reason: `DEFERRED_REGIONS_REMAIN`).
   - Ambiguous multipage stitching requiring manual review (Reason: `STITCH_REVIEW_REQUIRED`).
   - Printed arithmetic discrepancy detected (Reason: `SOURCE_ARITHMETIC_DISCREPANCY`).
   - Ambiguous calculation scope (Reason: `ARITHMETIC_SCOPE_AMBIGUOUS`).
   - Structural integrity check failures (Reason: `STRUCTURAL_CHECKS_FAILED`).
3. **`VERIFIED_WITH_WARNINGS`**:
   - Clean execution, but arithmetic checks were `NOT_APPLICABLE` (no summary rows).
   - Audited corrections were applied (`CORRECTED_WITH_EVIDENCE`).
   - High-precision decimal quantities detected (`HIGH_PRECISION_DECIMAL`).
4. **`VERIFIED`**:
   - Clean digital extraction, all pages inspected, zero deferred regions, zero anomalies, and all applicable arithmetic checks `PASSED`.

---

## 7. Mandatory Verbatim Disclaimer

Section 20 of the specification mandates that every non-fatal evaluation report must include the following verbatim disclaimer in `report.limitation_disclaimers` without paraphrase or modification:

> *"Structural integrity and internal arithmetic consistency were verified. This does not independently prove every source cell is correct and cannot rule out offsetting cell errors or errors in non-numeric text."*

### Why Arithmetic Consistency is Not Proof of Source Truth
A table where column values sum up to the printed total confirms internal mathematical consistency. However, it cannot guarantee that:
- Two offsetting errors (e.g. $+\$50$ and $-\$50$) did not cancel each other out.
- Non-numeric text (descriptions, names, invoice dates, account numbers) was printed correctly in the source document.
- The author of the original PDF did not enter completely incorrect starting figures.

---

## 8. Normalization vs. Evidence-Gated Correction

DocuStruct AI maintains a sharp architectural boundary between **normalization** and **correction**:

| Attribute | Normalization (`normalizer.py`) | Correction (`table_reconstructor.py`) |
| :--- | :--- | :--- |
| **Purpose** | Parse format variations into typed representations. | Rectify character recognition or extraction artifacts. |
| **Scope** | Standard/Indian grouping, accounting negatives, leading zeros. | Misread glyphs (e.g., `'1OO.OO'` $\to$ `'100.00'`). |
| **Source Text** | `raw_value` is never altered. | `raw_value` remains strictly immutable. |
| **Downstream Value** | Written to `accepted_value`. | Written to `accepted_value` ONLY with independent evidence. |
| **Evidence Contract** | Deterministic string parsing. | Must come from `NATIVE_PDF_CHAR_STREAM`, `INDEPENDENT_WORD_COORDINATES`, or `VECTOR_GRID_GEOMETRY`. |
| **Auto-Balancing** | Strictly prohibited. | **Strictly prohibited**. Discrepancies are flagged, never forced. |

---

## 9. Current Extraction Limitations & Risks

- **Scanned-Only Content**: Phase 1 contains no OCR engine. Scanned pages are safely identified and deferred (`OCR_REQUIRED_FOR_SCANNED_CONTENT`).
- **Borderless Tables**: Tables without ruling lines rely on coordinate-interval clustering. Pages with irregular word gaps or multi-line prose paragraphs near tables may require human review.
- **Multi-Line Wrapped Text**: Text wrapped across multiple lines within a single cell may be extracted as separate rows if line heights match row spacing.
- **Custom Font Encodings**: Non-standard or embedded Type 3 font glyph mappings that produce private unicode points (garbled text) are detected and escalated to `EMPTY_OR_UNREADABLE`.

---

## 10. Running the Unit Test Suite

The test suite consists of 161 comprehensive unit and integration tests across 8 test modules:

```powershell
# Run the entire test suite
python -m pytest backend/tests

# Run with verbose output and test timing
python -m pytest -v backend/tests
```

### Test Coverage Structure
- `test_step_1_1_config.py` — Settings, calibration, and thresholds.yaml loading.
- `test_step_1_2_status_and_gates.py` — State enums, domain model serialization, raw_value immutability.
- `test_normalizer_integrity.py` — Number grouping, accounting negatives, leading zeros, formula-risk prefix ordering.
- `test_step_1_3_security_gate.py` — File limits, encryption/corrupt PDF rejection, workspace isolation, path traversal.
- `test_step_1_4_page_router.py` — Page signal extraction, digital/scanned/hybrid routing, handle closure.
- `test_step_1_5_digital_extractor.py` — Ruled and borderless digital extraction, duplicate row preservation.
- `test_step_1_6_table_reconstructor.py` — 7-factor stitch engine, repeated header stripping, evidence-gated corrections.
- `test_quality_gate.py` — Exact Decimal arithmetic validation, discrepancy reporting, conservative decision precedence.
- `test_phase1_pipeline.py` — End-to-end integration across all document layouts, error handling, and handle safety.

---

## 11. Standalone Regression Evaluation Harness

DocuStruct AI includes an independent evaluation harness to benchmark extraction quality against reference cases:

```powershell
# Run the evaluation harness using builtin synthetic benchmark cases
python backend/tests/evaluation/regression_harness.py

# Run against a directory of custom evaluation cases (*.json)
python backend/tests/evaluation/regression_harness.py --cases-dir path\to\cases --output-json results.json
```

### Non-Negotiable Audit Integrity Rule (`UNMEASURED` Policy)
Under Section 21 and NFR-04, **if no manually verified ground-truth reference dataset is provided, the harness strictly reports:**

```
Real-World Acc: UNMEASURED
```

Synthetic test fixtures and unit tests prove code correctness and behavioral compliance, but they must **never** be misrepresented or reported as real-world document extraction accuracy.

---

## 12. Windows File-Handle Safety

Windows mandates strict file locking. Deleting an open file or directory raises a `PermissionError`. To ensure guaranteed resource safety:
- All PyMuPDF (`fitz.Document`) handles are closed inside strict `finally:` blocks.
- All `pdfplumber.PDF` instances are opened using `with pdfplumber.open(...)` context managers or guaranteed `finally: pdf.close()` blocks.
- The isolated job workspace is cleaned up in the pipeline's top-level `finally:` block.
- The original input file path is checked before cleanup to ensure the user's source PDF is **never deleted**.

---

## 13. License

Internal Enterprise Specification — DocuStruct AI Phase 1.
