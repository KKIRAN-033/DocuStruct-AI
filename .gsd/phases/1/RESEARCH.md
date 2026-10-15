# Phase 1 Research: Foundation, Domain Models & Ingestion Security

## Overview
Phase 1 establishes the foundational infrastructure, configuration loading, state enumerations, Pydantic v2 domain models, PDF security gate, and initial test suite for DocuStruct AI according to `MASTER_DIRECTIVE.md` (Sections 1–10, 19).

---

## 1. Environment & Packaging Architecture

### Python Version Compatibility
- **Target**: Python 3.11 (with compatibility verified for Python >=3.10 and <3.13).
- **Packaging Standard**: `pyproject.toml` using `setuptools.build_meta` with package directory mapping to `app`.
- **Approved Dependencies**:
  ```text
  pydantic>=2.7,<3.0
  pydantic-settings>=2.2
  PyYAML>=6.0
  PyMuPDF>=1.24.0
  pdfplumber>=0.11.0
  rapidfuzz>=3.9.0
  pytest>=8.2.0
  ```
- **Prohibited**: No OCR libraries, no web frameworks (FastAPI/Flask), no databases, no Excel libraries (`openpyxl`, `pandas`), no external binary tools (Poppler, Ghostscript, libmagic).

---

## 2. Configuration & Calibration System (`backend/app/config/`)

### Design & Path Independence
- `settings.py`: Uses `pydantic_settings.BaseSettings` with `SettingsConfigDict(env_prefix="DOCUSTRUCT_")`.
- `thresholds.yaml`: Centralized threshold configuration parsed with `yaml.safe_load`.
- `calibration.py`: `CalibrationConfig` validated by Pydantic v2.
- **Path Independence**: Base paths must resolve relative to `Path(__file__).resolve()` or an explicit project root environment override, ensuring tests pass regardless of current working directory (`CWD`).
- **Memory Instrumentation**: Optional `tracemalloc` tracking recorded in `peak_python_heap_bytes`. Explicit documentation that Python heap usage does not represent total operating-system process RAM.

---

## 3. State & Domain Model Contracts (`backend/app/models/`)

### State Enumerations (`state.py`)
All 9 enums inherit from `str, Enum` for JSON serialization:
1. `JobExecutionState`: `QUEUED`, `UNDERSTANDING`, `EXTRACTING`, `RECONSTRUCTING`, `VERIFYING`, `DIAGNOSING`, `CORRECTING`, `REVALIDATING`, `DELIVERING`, `COMPLETED`, `FAILED`
2. `VerificationStatus`: `VERIFIED`, `VERIFIED_WITH_WARNINGS`, `REVIEW_REQUIRED`, `FAILED`
3. `PageType`: `DIGITAL`, `SCANNED`, `HYBRID`, `EMPTY_OR_UNREADABLE`
4. `PageProcessingStatus`: `EXTRACTED`, `INCOMPLETE_DEFERRED_TO_OCR`, `EMPTY_PAGE`, `FAILED_PAGE`
5. `TablePresenceStatus`: `CONFIRMED_PRESENT`, `CONFIRMED_ABSENT`, `UNKNOWN_PENDING_OCR`
6. `ValidationOutcome`: `PASSED`, `PASSED_WITH_WARNINGS`, `FAILED_VALIDATION`, `NOT_APPLICABLE`
7. `StitchDecision`: `STITCH_CONFIRMED`, `STITCH_REJECTED`, `STITCH_REVIEW_REQUIRED`
8. `CellQualityStatus`: `EXTRACTED_AS_IS`, `CORROBORATED`, `CORRECTED_WITH_EVIDENCE`, `LOW_CONFIDENCE_WARNING`, `ANOMALY_FLAGGED`, `ILLEGIBLE_OR_MISSING`
9. `DataType`: `STRING`, `IDENTIFIER`, `INTEGER`, `DECIMAL`, `HIGH_PRECISION_DECIMAL`, `DATE`, `EMPTY`

### Domain Contracts (`domain.py`)
- **`BoundingBox`**: Validates `x0 <= x1`, `y0 <= y1`, `page_width > 0`, `page_height > 0`. Calculates normalized coordinates `norm_x0 = x0 / page_width`, etc.
- **`CellRecord`**: Invariant: `raw_value: str` is immutable. `numeric_decimal: Optional[Decimal]` must strictly use `decimal.Decimal` (never constructed from float). `accepted_value: str`.
- **`StitchAuditEvent`**, **`ValidationIssue`**, **`CorrectionRecord`**, **`PageProfile`**, **`CanonicalTable`**, **`PageExtractionResult`**, **`DocumentEvaluationReport`**.
- Order of declaration avoids forward-reference circularity; resolves forward references explicitly via `model_rebuild()` where needed.

---

## 4. PDF Security Gate & Windows Safety (`backend/app/ingestion/security_gate.py`)

### Security Invariants
1. File existence and regular file check (`path.is_file()`).
2. Maximum file size check: 25 MiB (`25 * 1024 * 1024` bytes).
3. PDF signature check: Header bytes must start with `%PDF-`.
4. Password/encryption rejection: Check `doc.is_encrypted` or `doc.needs_pass`; reject immediately.
5. Zero-page rejection: `doc.page_count == 0` rejected.
6. Page ceiling: `doc.page_count > 50` rejected.
7. Path traversal prevention: Sanitize filename with `pathlib.Path(filename).name`, resolve isolated UUID directory under `workspace_root`, verify `workspace_dir.resolve().is_relative_to(workspace_root.resolve())`.
8. File preservation: Never delete the user's original input file during cleanup.
9. Windows handle discipline: Use `fitz.open()` inside context managers or `try...finally` with explicit `doc.close()`.
